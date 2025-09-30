import json
import os
import sqlite3
from pathlib import Path

from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist


def test_run_backtest_error_no_stub_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEWSTON_CATALOG_PATH", str(tmp_path / "catalog.sqlite"))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

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
    bdir = Path(tmp_path) / "backtests" / run_id

    # With strict real-engine only behavior, and no bars_1Min.parquet (ensure_dataset creates bars_1m),
    # the job should mark ERROR and not write artifacts.
    assert out.get("status") == "ERROR"
    assert not (bdir / "metrics.json").exists()
    assert not (bdir / "equity.parquet").exists()
    assert not (bdir / "orders.parquet").exists()
    assert not (bdir / "fills.parquet").exists()
    assert (bdir / "run-manifest.json").exists()

    # Catalog rows
    db_path = Path(os.environ["HEWSTON_CATALOG_PATH"])  # set above
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        run = conn.execute("SELECT * FROM backtests WHERE backtest_id = ?", (run_id,)).fetchone()
        assert run is not None
        assert run["status"] == "ERROR"
        # No artifact paths should be set
        assert run["metrics_path"] is None
        assert run["equity_path"] is None
        assert run["orders_path"] is None
        assert run["fills_path"] is None
        assert run["run_manifest_path"].endswith("run-manifest.json")
        assert run["duration_ms"] >= 0

