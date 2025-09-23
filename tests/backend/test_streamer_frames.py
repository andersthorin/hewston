import asyncio
import os
from pathlib import Path

import pytest

from backend.adapters.databento import ensure_dataset
from backend.jobs.run_backtest import run_backtest_and_persist
from backend.services.streamer import produce_frames


def test_streamer_produces_frames_decimated(tmp_path, monkeypatch):
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

    async def _collect():
        frames = []
        async for fr in produce_frames(run_id=run_id, fps=30, speed=1.0, realtime=False):
            frames.append(fr)
        return frames

    frames = asyncio.run(_collect())
    # We have at least one frame (our stub equity has >=2 points)
    assert len(frames) >= 1
    f0 = frames[0]
    assert f0.t == "frame"
    assert isinstance(f0.ts, str)
    assert f0.equity is None or "value" in f0.equity
    # Orders array present (may be 0 or more)
    assert isinstance(f0.orders, list)

