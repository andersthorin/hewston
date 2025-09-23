import json
import os
import sqlite3
from pathlib import Path

from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist


def test_run_backtest_persists_artifacts_and_catalog(tmp_path, monkeypatch):
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
    # Artifacts exist
    assert (bdir / "metrics.json").exists()
    assert (bdir / "equity.parquet").exists()
    assert (bdir / "orders.parquet").exists()
    assert (bdir / "fills.parquet").exists()
    assert (bdir / "run-manifest.json").exists()

    # Catalog rows
    db_path = Path(os.environ["HEWSTON_CATALOG_PATH"])  # set above
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        assert run is not None
        assert run["status"] == "DONE"
        # Paths recorded
        assert run["metrics_path"].endswith("metrics.json")
        assert run["equity_path"].endswith("equity.parquet")
        assert run["orders_path"].endswith("orders.parquet")
        assert run["fills_path"].endswith("fills.parquet")
        assert run["run_manifest_path"].endswith("run-manifest.json")
        assert run["duration_ms"] >= 0

        m = conn.execute("SELECT * FROM run_metrics WHERE run_id = ?", (run_id,)).fetchone()
        assert m is not None
        # Minimal metrics fields present
        assert m["total_return"] is not None
        assert m["max_drawdown"] is not None

