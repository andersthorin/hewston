import json
import os
from pathlib import Path

from backend.services.backtests import create_backtest_service


def test_manifest_contains_strategies_for_multi_strategy(tmp_path, monkeypatch):
    # Route all data paths into a temp HEWSTON_DATA_DIR
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))

    body = {
        "strategy_id": "sma_crossover",  # compat field
        "strategies": [
            {"strategy_id": "momentum_v1", "params": {"window": 10}},
            {"strategy_id": "rsi_mean_reversion_v1", "params": {"rsi_period": 7}},
        ],
        "symbol": "AAPL",
        "year": 2024,
    }
    payload, code = create_backtest_service(body, idempotency_key="multi-1")
    assert code == 202
    run_id = payload["run_id"]

    # Locate the manifest from artifacts path in catalog via returned payload (service returns only run_id)
    # We reconstruct expected manifest path from service default path pattern
    # Fallback to scanning tmp_path for run_id manifest
    # Locate manifest anywhere under HEWSTON_DATA_DIR
    candidates = [p for p in tmp_path.rglob("run-manifest.json") if run_id in str(p)]
    assert candidates, f"manifest file not found under {tmp_path} for run {run_id}"
    manifest_path = candidates[0]
    data = json.loads(manifest_path.read_text())

    strategies = data.get("strategies") or []
    assert isinstance(strategies, list) and len(strategies) == 2
    sids = {s.get("strategy_id") for s in strategies}
    assert {"momentum_v1", "rsi_mean_reversion_v1"} <= sids

