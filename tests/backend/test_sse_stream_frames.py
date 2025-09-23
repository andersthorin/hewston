import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist


def test_sse_stream_frames_basic(tmp_path, monkeypatch):
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
    buf = ""
    with client.stream("GET", f"/backtests/{run_id}/stream") as r:
        assert r.status_code == 200
        # Read a few chunks and look for a frame
        for chunk in r.iter_text():
            buf += chunk
            if "event: frame" in buf and '"t":"frame"' in buf:
                break
    assert "event: frame" in buf
    assert '"t": "frame"' in buf

