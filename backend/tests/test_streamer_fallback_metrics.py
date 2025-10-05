import polars as pl
import pytest
from pathlib import Path

from backend.services import streamer as streamer_mod


@pytest.mark.asyncio
async def test_streamer_fallback_metrics_when_no_artifact(tmp_path: Path, monkeypatch):
    # Prepare equity with simple growth
    eq_df = pl.DataFrame({
        "ts_utc": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z", "2024-01-01T00:02:00Z"],
        "value": [100.0, 101.0, 102.0],
    })
    eq_path = tmp_path / "equity.parquet"
    eq_df.write_parquet(eq_path)

    ord_path = tmp_path / "orders.parquet"
    pl.DataFrame({"ts_utc": [], "id": []}).write_parquet(ord_path)

    # Monkeypatch resolver without metrics.json
    def _fake_resolve_artifacts(run_id: str):
        return {
            "equity": str(eq_path),
            "orders": str(ord_path),
            "fills": None,
            "metrics": None,
        }, None

    monkeypatch.setattr(streamer_mod, "_resolve_artifacts", _fake_resolve_artifacts)

    frames = []
    async for fr in streamer_mod.produce_frames(run_id="X", realtime=False, cadence="1m"):
        frames.append(fr)

    assert len(frames) == 3
    # Fallback should still provide total_return and drawdown and sharpe (possibly null if too few points)
    assert frames[-1].metrics is not None
    assert "total_return" in frames[-1].metrics
    assert frames[-1].metrics["total_return"] is not None
    assert "drawdown" in frames[-1].metrics

