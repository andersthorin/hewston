import os
import time
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.adapters.databento import ensure_dataset


def wait_for_status(run_id: str, expect: str, timeout_s: float = 5.0):
    client = TestClient(app)
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = client.get(f"/backtests/{run_id}")
        if r.status_code == 200 and r.json().get("status") == expect:
            return True
        time.sleep(0.1)
    return False


def test_post_backtests_idempotent(tmp_path, monkeypatch):
    # Redirect data dir and set API key for subprocess
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEWSTON_CATALOG_PATH", str(tmp_path / "catalog.sqlite"))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

    # Ensure dataset upfront
    dsid = ensure_dataset("AAPL", 2023, force=False)

    client = TestClient(app)

    body = {
        "dataset_id": dsid,
        "strategy_id": "sma_crossover",
        "params": {"fast": 2, "slow": 3},
        "seed": 42,
        "speed": 60,
    }

    r1 = client.post("/backtests", json=body)
    assert r1.status_code == 202
    run_id = r1.json()["run_id"]

    # Same body should be idempotent (EXISTS)
    r2 = client.post("/backtests", json=body)
    assert r2.status_code == 200
    assert r2.json()["run_id"] == run_id
    assert r2.json()["status"] == "EXISTS"

    # Idempotency-Key header also maps to same run
    r3 = client.post("/backtests", json=body, headers={"Idempotency-Key": "k1"})
    if r3.status_code == 202:
        # First time header used, either 202 (new mapping) or 200 (existing input hash)
        assert r3.json()["run_id"] == run_id
    else:
        assert r3.status_code == 200
        assert r3.json()["run_id"] == run_id

    # Wait for run to complete
    assert wait_for_status(run_id, "DONE", timeout_s=5.0)

    # Check catalog row reflects DONE
    db_path = Path(os.environ["HEWSTON_CATALOG_PATH"])  # set above
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        assert row is not None and row["status"] == "DONE"

