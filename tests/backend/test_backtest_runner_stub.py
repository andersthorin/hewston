import os
from pathlib import Path

from backend.adapters.databento import ensure_dataset
from backend.adapters.nautilus import NautilusBacktestRunner


def test_runner_produces_results(tmp_path, monkeypatch):
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

    dsid = ensure_dataset("AAPL", 2023, force=False)
    assert dsid == "AAPL-2023-1m"

    runner = NautilusBacktestRunner()
    res = runner.run(dataset_id=dsid, strategy_id="sma_crossover", params={"fast": 2, "slow": 3}, seed=42)
    assert isinstance(res, dict)
    assert "orders" in res and "fills" in res and "equity" in res and "metrics" in res
    # Our stub should produce at least one order/fill even on tiny data
    assert len(res["orders"]) >= 1
    assert len(res["fills"]) >= 1
    assert len(res["equity"]) >= 2
    assert "total_return" in res["metrics"] and "max_drawdown" in res["metrics"]

