"""Backtest HTTP and WebSocket routes."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime as _dt
from typing import Any

from fastapi import APIRouter, Header, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd

from backend.api.controllers.backtests import (
    create_backtest as create_backtest_ctrl,
    get_backtest as get_backtest_ctrl,
    list_backtests as list_backtests_ctrl,
)
from backend.constants import DEFAULT_FPS

def _json_default(o):
    try:
        if isinstance(o, _dt | pd.Timestamp):
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
    """Create a backtest via controller.

    Returns JSON with created resource or error payload.
    """
    raw = b""
    try:
        raw = await request.body()
        body = json.loads(raw.decode("utf-8") or "{}")
    except Exception as e:
        logger.exception(
            "create_backtest.json_error",
            extra={
                "content_type": request.headers.get("content-type"),
                "raw_sample": (
                    raw[:200].decode("utf-8", "ignore")
                    if isinstance(raw, bytes | bytearray)
                    else str(raw)
                ),
                "error": str(e),
            },
        )
        with contextlib.suppress(Exception):
            logger.error(
                "create_backtest.body raw=%r content_type=%s",
                raw[:200],
                request.headers.get("content-type"),
            )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "BAD_REQUEST", "message": "invalid JSON"}},
        )

    # Delegate to module controller (pilot exemplar)

    payload, code = create_backtest_ctrl(
        body if isinstance(body, dict) else {}, idempotency_key
    )
    if status.HTTP_200_OK <= code < status.HTTP_300_MULTIPLE_CHOICES:
        return JSONResponse(status_code=code, content=payload)
    # Error branch
    return JSONResponse(status_code=code, content=payload)


@router.get("/backtests")
async def list_backtests(
    limit: int = 20,
    offset: int = 0,
    symbol: str | None = None,
    strategy_id: str | None = None,
    run_from: str | None = Query(None, alias="run_from"),
    run_to: str | None = Query(None, alias="run_to"),
    order: str | None = None,
):
    """List backtests with optional filters and pagination."""
    logger.info(
        "list_backtests",
        extra={
            "symbol": symbol,
            "strategy_id": strategy_id,
            "run_from": run_from,
            "run_to": run_to,
            "limit": limit,
            "offset": offset,
            "order": order,
        },
    )
    return list_backtests_ctrl(
        symbol=symbol,
        strategy_id=strategy_id,
        from_date=run_from,
        to_date=run_to,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/backtests/{run_id}")
async def get_backtest(run_id: str):
    """Get a single backtest by ID."""
    data = get_backtest_ctrl(run_id)
    if not data:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}},
        )
    return data


@router.get("/backtests/{run_id}/metrics")
async def get_backtest_metrics(run_id: str):
    """Return metrics.json for a run.

    Shape: a flat JSON object with numeric fields (arbitrary keys allowed).
    """
    run = get_backtest_ctrl(run_id)
    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}},
        )
    metrics_path = (run.get("artifacts") or {}).get("metrics_path")
    try:
        import os

        if not metrics_path:
            logger.warning("get_metrics.missing_path", extra={"run_id": run_id})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_MISSING",
                        "message": f"metrics_path missing for backtest {run_id}",
                    }
                },
            )
        if not os.path.isfile(metrics_path):
            logger.warning(
                "get_metrics.file_not_found", extra={"run_id": run_id, "path": metrics_path}
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_NOT_FOUND",
                        "message": f"metrics file not found at {metrics_path}",
                    }
                },
            )
        with open(metrics_path) as f:
            data = json.load(f)
        return JSONResponse(status_code=status.HTTP_200_OK, content=data)
    except Exception as e:
        logger.exception("get_metrics.error", extra={"run_id": run_id, "error": str(e)[:200]})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL", "message": "failed to load metrics"}},
        )


@router.get("/backtests/{run_id}/equity")
async def get_backtest_equity(run_id: str):
    """Return equity curve under { equity: [{timestamp, equity, drawdown?}] }.

    Parquet schema expected: columns ['ts_utc', 'value'] where ts_utc is datetime-like.
    """
    run = get_backtest_ctrl(run_id)
    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}},
        )
    eq_path = (run.get("artifacts") or {}).get("equity_path")
    try:
        import os

        if not eq_path:
            logger.warning("get_equity.missing_path", extra={"run_id": run_id})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_MISSING",
                        "message": f"equity_path missing for backtest {run_id}",
                    }
                },
            )
        if not os.path.isfile(eq_path):
            logger.warning("get_equity.file_not_found", extra={"run_id": run_id, "path": eq_path})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_NOT_FOUND",
                        "message": f"equity file not found at {eq_path}",
                    }
                },
            )
        import polars as pl

        df = pl.read_parquet(eq_path)
        # Accept legacy naming too; normalize to 'ts_utc'
        if "ts" in df.columns and "ts_utc" not in df.columns:
            df = df.rename({"ts": "ts_utc"})
        cols = [c for c in ["ts_utc", "value", "drawdown"] if c in df.columns]
        df = df.select(cols)
        points = []
        for r in df.to_dicts():
            ts = r.get("ts_utc")
            # Normalize to ISO string
            try:
                iso = pd.to_datetime(ts, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                iso = str(ts)
            pt = {"timestamp": iso, "equity": float(r.get("value", 0.0))}
            if "drawdown" in r and r.get("drawdown") is not None:
                with contextlib.suppress(Exception):
                    pt["drawdown"] = float(r.get("drawdown"))
            points.append(pt)

        return JSONResponse(status_code=status.HTTP_200_OK, content={"equity": points})
    except Exception as e:
        logger.exception("get_equity.error", extra={"run_id": run_id, "error": str(e)[:200]})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": {"code": "INTERNAL", "message": "failed to load equity"}},
        )


@router.get("/backtests/{run_id}/orders")
async def get_backtest_orders(run_id: str):
    """Return orders as list under { orders: [...] }.

    Parquet schema suggested in docs: ts_utc, side, qty, price, order_id,
    type, time_in_force, symbol? Response maps to aggregator-friendly shape.
    """
    run = get_backtest_ctrl(run_id)
    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}},
        )
    path = (run.get("artifacts") or {}).get("orders_path")
    try:
        import os

        if not path:
            logger.warning("get_orders.missing_path", extra={"run_id": run_id})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_MISSING",
                        "message": f"orders_path missing for backtest {run_id}",
                    }
                },
            )
        if not os.path.isfile(path):
            logger.warning("get_orders.file_not_found", extra={"run_id": run_id, "path": path})
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "ARTIFACT_NOT_FOUND",
                        "message": f"orders file not found at {path}",
                    }
                },
            )
        import polars as pl

        df = pl.read_parquet(path)
        rows = []
        for r in df.to_dicts():
            ts = r.get("ts_utc") or r.get("timestamp") or r.get("ts")
            try:
                iso = pd.to_datetime(ts, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                iso = str(ts) if ts is not None else ""
            rows.append(
                {
                    "order_id": str(r.get("order_id", "")),
                    "timestamp": iso,
                    "symbol": str(r.get("symbol", "")),
                    "side": str(r.get("side", "")),
                    "quantity": int(
                        r.get("qty") if r.get("qty") is not None else r.get("quantity") or 0
                    ),
                    "price": float(r.get("price", 0.0) or 0.0),
                    "order_type": str(r.get("type") or r.get("order_type") or ""),
                    "status": str(r.get("status") or "FILLED"),
                    "commission": (
                        float(r.get("commission")) if r.get("commission") is not None else None
                    ),
                }
            )

        return JSONResponse(status_code=200, content={"orders": rows})
    except Exception as e:
        logger.exception("get_orders.error", extra={"run_id": run_id, "error": str(e)[:200]})
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL", "message": "failed to load orders"}},
        )


HEARTBEAT_SECONDS = 5.0


class _BacktestWSHandler:
    def __init__(self, websocket: WebSocket, run_id: str):
        self.ws = websocket
        self.run_id = run_id
        self.frames_sent = 0
        self.last_dropped = 0
        self.ready = False
        self.hb: asyncio.Task | None = None
        self.player_task: asyncio.Task | None = None

    async def _send_err(self, code: str, msg: str) -> None:
        with contextlib.suppress(Exception):
            await self.ws.send_text(json.dumps({"t": "err", "code": code, "msg": msg}))

    def _frame_payload(self, fr) -> dict:
        return {
            "t": fr.t,
            "ts": fr.ts,
            "ohlc": fr.ohlc,
            "orders": fr.orders,
            "equity": fr.equity,
            "metrics": fr.metrics,
            "dropped": fr.dropped,
            "total_frames": getattr(fr, "total_frames", None),
        }

    async def _start_player(self) -> None:
        if not self.ready:
            logger.debug(
                "ws.play_ignored", extra={"run_id": self.run_id, "reason": "frontend_not_ready"}
            )
            return
        if self.player_task and not self.player_task.done():
            return

        from backend.services.streamer import produce_frames

        async def _run():
            try:
                logger.info("ws.stream_start", extra={"run_id": self.run_id})
                async for fr in produce_frames(
                    run_id=self.run_id, fps=DEFAULT_FPS, speed=1.0, realtime=True, cadence="1h"
                ):
                    await self.ws.send_text(_json_dumps(self._frame_payload(fr)))
                    self.frames_sent += 1
                    self.last_dropped = fr.dropped or 0
                logger.info(
                    "ws.stream_complete",
                    extra={"run_id": self.run_id, "frames_sent": self.frames_sent},
                )
            except Exception as e:
                await self._send_err("STREAM_ERROR", str(e)[:200])
                return

        self.player_task = asyncio.create_task(_run())

    async def _handle_payload(self, payload: dict[str, Any]) -> None:
        t = payload.get("t")
        if t == "ready":
            self.ready = True
            logger.info("ws.ready_received", extra={"run_id": self.run_id})
            await self.ws.send_text(json.dumps({"t": "ready_ack"}))
            await self._start_player()
            return
        if t == "ctrl":
            cmd = payload.get("cmd")
            if cmd not in {"play", "pause", "seek", "speed"}:
                await self._send_err("VALIDATION", "invalid ctrl.cmd")
                return
            payload["echo"] = True
            await self.ws.send_text(json.dumps(payload))
            if cmd == "play":
                await self._start_player()
            elif cmd == "pause" and self.player_task and not self.player_task.done():
                self.player_task.cancel()
                with contextlib.suppress(BaseException):
                    await self.player_task
            return
        await self._send_err("VALIDATION", "unsupported message")

    async def run(self) -> None:
        await self.ws.accept()
        logger.info("ws.connect", extra={"run_id": self.run_id})
        self.hb = asyncio.create_task(_heartbeat_task(self.ws))
        try:
            while True:
                data = await self.ws.receive_text()
                try:
                    payload: dict[str, Any] = json.loads(data)
                except json.JSONDecodeError:
                    await self._send_err("VALIDATION", "invalid JSON")
                    continue
                await self._handle_payload(payload)
        except WebSocketDisconnect:
            logger.info(
                "ws.disconnect",
                extra={
                    "run_id": self.run_id,
                    "frames_sent": self.frames_sent,
                    "frames_dropped": self.last_dropped,
                },
            )
        finally:
            if self.hb:
                self.hb.cancel()
                with contextlib.suppress(BaseException):
                    await self.hb
            if self.player_task and not self.player_task.done():
                self.player_task.cancel()
                with contextlib.suppress(BaseException):
                    await self.player_task


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
    """WS endpoint with heartbeat, ctrl echo, and optional frame streaming."""
    handler = _BacktestWSHandler(websocket, run_id)
    await handler.run()


@router.get("/backtests/{run_id}/stream")
async def stream_backtest(run_id: str, speed: float = 1.0):
    """Server-sent events stream of backtest frames (for debugging/dev)."""
    from backend.services.streamer import produce_frames

    async def gen():
        frames_sent = 0
        last_dropped = 0
        try:
            async for fr in produce_frames(
                run_id=run_id, fps=DEFAULT_FPS, speed=float(speed), realtime=True, cadence="1h"
            ):
                payload = {
                    "t": fr.t,
                    "ts": fr.ts,
                    "ohlc": fr.ohlc,
                    "orders": fr.orders,
                    "equity": fr.equity,
                    "metrics": fr.metrics,
                    "dropped": fr.dropped,
                    "total_frames": getattr(fr, "total_frames", None),
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
            with contextlib.suppress(Exception):
                logger.info(
                    "sse.end",
                    extra={
                        "run_id": run_id,
                        "frames_sent": frames_sent,
                        "frames_dropped": last_dropped,
                    },
                )

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)
