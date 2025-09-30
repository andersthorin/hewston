import os
from pathlib import Path

from backend.adapters.databento import ensure_dataset
from backend.adapters.nautilus import NautilusBacktestRunner
import pytest


def test_runner_no_stub_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

    dsid = ensure_dataset("AAPL", 2023, force=False)
    assert dsid == "AAPL-2023-1m"

    runner = NautilusBacktestRunner()
    # Without nautilus-trader installed or without strict bars_1Min.parquet,
    # the runner must raise and not fallback to a stub.
    with pytest.raises(BaseException):
        runner.run(dataset_id=dsid, strategy_id="sma_crossover", params={"fast": 2, "slow": 3}, seed=42)

