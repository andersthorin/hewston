from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatasetManifest(BaseModel):
    # Placeholder for future fields; keep as dict for now
    meta: dict[str, Any] = Field(default_factory=dict)


class Dataset(BaseModel):
    dataset_id: str
    symbol: str
    from_date: str | None = None
    to_date: str | None = None
    manifest: DatasetManifest | None = None


# Canonical models (backtests)
class BacktestManifest(BaseModel):
    """Canonical manifest model for a backtest."""

    meta: dict[str, Any] = Field(default_factory=dict)


class BacktestMetrics(BaseModel):
    """Canonical metrics model for a backtest."""

    metrics: dict[str, Any] = Field(default_factory=dict)


class Backtest(BaseModel):
    """Canonical Backtest model.

    Note: `run_from` and `run_to` are time window semantics and intentionally keep
    their established names per project-wide directive.
    """

    run_id: str  # identifier retained as `run_id` for cross-layer compatibility
    dataset_id: str | None = None
    strategy_id: str
    status: str
    created_at: str
    duration_ms: int | None = None
    manifest: BacktestManifest | None = None
    metrics: BacktestMetrics | None = None


class BacktestSummary(BaseModel):
    """Canonical summary for listing/filtering backtests."""

    run_id: str
    created_at: str
    strategy_id: str
    status: str
    symbol: str | None = None
    # Field names standardized; keep `run_from`/`run_to`
    run_from: str | None = None
    run_to: str | None = None
    duration_ms: int | None = None
