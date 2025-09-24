from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime as _dt
import pandas as pd
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.backtests import list_runs_service, get_run_service

from uuid import uuid4
from fastapi import Body, Header, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse, StreamingResponse


def _json_default(o):
    try:
        if isinstance(o, (_dt, pd.Timestamp)):
            return pd.to_datetime(o, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    # Fallback to string
    try:
        return str(o)
    except Exception:
        return ""

def _json_dumps(obj: dict) -> str:
    return json.dumps(obj, default=_json_default)

logger = logging.getLogger(__name__)
router = APIRouter()

# Heartbeat interval (seconds). Tests may monkeypatch this.

@router.post("/backtests")
async def create_backtest(
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    raw = b""
    try:
        raw = await request.body()
        body = json.loads(raw.decode("utf-8") or "{}")
    except Exception as e:
        logger.exception("create_backtest.json_error", extra={
            "content_type": request.headers.get("content-type"),
            "raw_sample": (raw[:200].decode("utf-8", "ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)),
            "error": str(e),
        })
        try:
            logger.error(f"create_backtest.body raw={raw[:200]!r} content_type={request.headers.get('content-type')}")
        except Exception:
            pass
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "BAD_REQUEST", "message": "invalid JSON"}},
        )

    from backend.services.backtests import create_backtest_service

    payload, code = create_backtest_service(body if isinstance(body, dict) else {}, idempotency_key)
    if 200 <= code < 300:
        return JSONResponse(status_code=code, content=payload)
    # Error branch
    return JSONResponse(status_code=code, content=payload)


@router.get("/backtests")
async def list_backtests(
    limit: int = 20,
    offset: int = 0,
    symbol: str | None = None,
    strategy_id: str | None = None,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    order: str | None = None,
):
    logger.info(
        "list_backtests",
        extra={
            "symbol": symbol,
            "strategy_id": strategy_id,
            "from": from_date,
            "to": to_date,
            "limit": limit,
            "offset": offset,
            "order": order,
        },
    )
    return list_runs_service(
        symbol=symbol,
        strategy_id=strategy_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/backtests/{run_id}")
async def get_backtest(run_id: str):
    data = get_run_service(run_id)
    if not data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}},
        )
    return data

HEARTBEAT_SECONDS = 5.0


async def _heartbeat_task(ws: WebSocket) -> None:
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            await ws.send_text(json.dumps({"t": "hb"}))
    except Exception:
        # Socket closed or send failed; exit quietly
        return


@router.websocket("/backtests/{run_id}/ws")
async def backtests_ws_echo(websocket: WebSocket, run_id: str) -> None:
    """
    WS endpoint with heartbeat, ctrl echo, and optional frame streaming when available.
    - Sends periodic {"t":"hb"}
    - Echoes {"t":"ctrl", ...} with {"echo": true}
    - On {"t":"ctrl","cmd":"play"} attempts to stream frames for run_id if artifacts exist
    - Sends {"t":"err", code:"VALIDATION", msg:"..."} on invalid payloads
    """
    await websocket.accept()
    logger.info("ws.connect", extra={"run_id": run_id})

    from backend.services.streamer import produce_frames

    hb = asyncio.create_task(_heartbeat_task(websocket))
    player_task: asyncio.Task | None = None
    frames_sent = 0
    last_dropped = 0

    async def _start_player() -> None:
        nonlocal player_task, frames_sent, last_dropped
        if player_task and not player_task.done():
            return
        async def _run():
            nonlocal frames_sent, last_dropped
            try:
                async for fr in produce_frames(run_id=run_id, fps=30, speed=1.0, realtime=False):
                    d = {
                        "t": fr.t,
                        "ts": fr.ts,
                        "ohlc": fr.ohlc,
                        "orders": fr.orders,
                        "equity": fr.equity,
                        "dropped": fr.dropped,
                    }
                    await websocket.send_text(_json_dumps(d))
                    frames_sent += 1
                    last_dropped = fr.dropped or 0
            except Exception as e:
                try:
                    await websocket.send_text(_json_dumps({"t": "err", "code": "STREAM_ERROR", "msg": str(e)[:200]}))
                except Exception:
                    pass
                return
        player_task = asyncio.create_task(_run())

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload: dict[str, Any] = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"t": "err", "code": "VALIDATION", "msg": "invalid JSON"})
                )
                continue

            t = payload.get("t")
            if t == "ctrl":
                cmd = payload.get("cmd")
                if cmd not in {"play", "pause", "seek", "speed"}:
                    await websocket.send_text(
                        json.dumps({"t": "err", "code": "VALIDATION", "msg": "invalid ctrl.cmd"})
                    )
                    continue
                # Echo back for compatibility
                payload["echo"] = True
                await websocket.send_text(json.dumps(payload))
                # Handle simple play/pause
                if cmd == "play":
                    await _start_player()
                elif cmd == "pause":
                    if player_task and not player_task.done():
                        player_task.cancel()
                        with contextlib.suppress(BaseException):
                            await player_task
                # seek/speed are acknowledged via echo; applied in future stories
            else:
                await websocket.send_text(
                    json.dumps({"t": "err", "code": "VALIDATION", "msg": "unsupported message"})
                )
    except WebSocketDisconnect:
        logger.info("ws.disconnect", extra={"run_id": run_id, "frames_sent": frames_sent, "frames_dropped": last_dropped})
    finally:
        hb.cancel()
        with contextlib.suppress(BaseException):
            await hb
        if player_task and not player_task.done():
            player_task.cancel()
            with contextlib.suppress(BaseException):
                await player_task


@router.get("/backtests/{run_id}/stream")
async def stream_backtest(run_id: str, speed: float = 1.0):
    from backend.services.streamer import produce_frames

    async def gen():
        frames_sent = 0
        last_dropped = 0
        try:
            async for fr in produce_frames(run_id=run_id, fps=30, speed=float(speed), realtime=False):
                payload = {
                    "t": fr.t,
                    "ts": fr.ts,
                    "ohlc": fr.ohlc,
                    "orders": fr.orders,
                    "equity": fr.equity,
                    "dropped": fr.dropped,
                }
                yield f"event: frame\ndata: {_json_dumps(payload)}\n\n"
                frames_sent += 1
                last_dropped = fr.dropped or 0
            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            # Emit error event and finish
            err = {"code": "STREAM_ERROR", "msg": str(e)[:200]}
            yield f"event: error\ndata: {_json_dumps(err)}\n\n"
        finally:
            try:
                logger.info("sse.end", extra={"run_id": run_id, "frames_sent": frames_sent, "frames_dropped": last_dropped})
            except Exception:
                pass

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)
