from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Heartbeat interval (seconds). Tests may monkeypatch this.
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
    S1.2 echo endpoint with heartbeat and validation.
    - Sends periodic {"t":"hb"}
    - Echoes {"t":"ctrl", ...} with {"echo": true}
    - Sends {"t":"err", code:"VALIDATION", msg:"..."} on invalid payloads
    """
    await websocket.accept()
    logger.info("ws.connect", extra={"run_id": run_id})

    hb = asyncio.create_task(_heartbeat_task(websocket))
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
                payload["echo"] = True
                await websocket.send_text(json.dumps(payload))
            else:
                await websocket.send_text(
                    json.dumps({"t": "err", "code": "VALIDATION", "msg": "unsupported message"})
                )
    except WebSocketDisconnect:
        logger.info("ws.disconnect", extra={"run_id": run_id})
    finally:
        hb.cancel()
        # In Python 3.11, CancelledError may not derive from Exception; be broad here.
        with contextlib.suppress(BaseException):
            await hb
