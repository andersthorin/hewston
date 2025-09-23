import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist


def test_ws_stream_frames_basic(tmp_path, monkeypatch):
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEWSTON_CATALOG_PATH", str(tmp_path / "catalog.sqlite"))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

    # Prepare a finished run
    dsid = ensure_dataset("AAPL", 2023, force=False)
    out = run_backtest_and_persist(
        dataset_id=dsid,
        strategy_id="sma_crossover",
        params={"fast": 2, "slow": 3},
        seed=42,
        speed=60,
        slippage_fees={},
    )
    run_id = out["run_id"]

    client = TestClient(app)
    with client.websocket_connect(f"/backtests/{run_id}/ws") as ws:
        # Ask to play
        ws.send_json({"t": "ctrl", "cmd": "play"})
        # First receive should be echo; then frames
        t0 = time.time()
        got_frame = False
        while time.time() - t0 < 2.0:
            msg = ws.receive_json()
            if msg.get("t") == "frame":
                got_frame = True
                break
        assert got_frame, "did not receive frame over WS"
        ws.close()

