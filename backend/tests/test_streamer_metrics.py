"""Streamer uses precomputed metrics when available (happy path)."""

import json
from pathlib import Path

import polars as pl
import pytest

from backend.services import streamer as streamer_mod

EPS_12 = 1e-12
RET_1PCT = 0.01
PNL_5 = 5.0
FRAMES_EXPECTED = 2


@pytest.mark.asyncio
async def test_streamer_uses_precomputed_metrics(tmp_path: Path, monkeypatch):
    """Precomputed metrics in metrics.json should drive frame metrics."""
    # Prepare fake artifacts
    eq_path = tmp_path / "equity.parquet"
    ord_path = tmp_path / "orders.parquet"
    met_path = tmp_path / "metrics.json"

    # Two equity points, 1-minute apart
    eq_df = pl.DataFrame(
        {
            "ts_utc": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
            "value": [100.0, 101.0],
        }
    )
    eq_df.write_parquet(eq_path)

    # Empty orders
    pl.DataFrame({"ts_utc": [], "id": []}).write_parquet(ord_path)

    # Precomputed metrics artifact: series is list of [iso, metrics]
    series = [
        [
            "2024-01-01T00:00:00Z",
            {
                "return": None,
                "realized_pnl": None,
                "total_return": 0.0,
                "drawdown": 0.0,
                "sharpe": None,
                "win_rate": None,
            },
        ],
        [
            "2024-01-01T00:01:00Z",
            {
                "return": 0.01,
                "realized_pnl": 5.0,
                "total_return": 0.01,
                "drawdown": 0.0,
                "sharpe": 1.23,
                "win_rate": 1.0,
            },
        ],
    ]
    met_path.write_text(json.dumps({"series": series, "bar_interval_minutes": 1}))

    # Monkeypatch artifacts resolver to point to our temp files
    def _fake_resolve_artifacts(run_id: str):
        return {
            "equity": str(eq_path),
            "orders": str(ord_path),
            "fills": None,
            "metrics": str(met_path),
        }, None

    monkeypatch.setattr(streamer_mod, "_resolve_artifacts", _fake_resolve_artifacts)

    # Collect frames
    frames = []
    async for fr in streamer_mod.produce_frames(run_id="X", realtime=False, cadence="1m"):
        frames.append(fr)

    assert len(frames) == FRAMES_EXPECTED
    # First frame uses first metrics object
    assert frames[0].metrics["total_return"] == 0.0
    assert frames[0].metrics["return"] is None
    # Second frame uses second metrics object
    assert pytest.approx(frames[1].metrics["return"], rel=EPS_12) == RET_1PCT
    assert frames[1].metrics["realized_pnl"] == PNL_5
    assert frames[1].metrics["win_rate"] == 1.0
