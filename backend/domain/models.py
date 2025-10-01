from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class DatasetManifest(BaseModel):
    # Placeholder for future fields; keep as dict for now
    meta: Dict[str, Any] = Field(default_factory=dict)


class Dataset(BaseModel):
    dataset_id: str
    symbol: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    manifest: Optional[DatasetManifest] = None


# Canonical models (backtests)
class BacktestManifest(BaseModel):
    """Canonical manifest model for a backtest."""
    meta: Dict[str, Any] = Field(default_factory=dict)


class BacktestMetrics(BaseModel):
    """Canonical metrics model for a backtest."""
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Backtest(BaseModel):
    """Canonical Backtest model.

    Note: `run_from` and `run_to` are time window semantics and intentionally keep
    their established names per project-wide directive.
    """
    run_id: str  # identifier retained as `run_id` for cross-layer compatibility
    dataset_id: Optional[str] = None
    strategy_id: str
    status: str
    created_at: str
    duration_ms: Optional[int] = None
    manifest: Optional[BacktestManifest] = None
    metrics: Optional[BacktestMetrics] = None


class BacktestSummary(BaseModel):
    """Canonical summary for listing/filtering backtests."""
    run_id: str
    created_at: str
    strategy_id: str
    status: str
    symbol: Optional[str] = None
    # Field names standardized; keep `run_from`/`run_to`
    run_from: Optional[str] = None
    run_to: Optional[str] = None
    duration_ms: Optional[int] = None


