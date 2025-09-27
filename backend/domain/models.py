from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class DatasetManifest(BaseModel):
    # Placeholder for future fields; keep as dict for now
    meta: Dict[str, Any] = Field(default_factory=dict)


class Dataset(BaseModel):
    dataset_id: str
    symbol: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    manifest: Optional[DatasetManifest] = None


class RunManifest(BaseModel):
    # Placeholder; free-form for now
    meta: Dict[str, Any] = Field(default_factory=dict)


class RunMetrics(BaseModel):
    # Minimal placeholder metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    run_id: str
    dataset_id: Optional[str] = None
    strategy_id: str
    status: str
    created_at: str
    duration_ms: Optional[int] = None
    manifest: Optional[RunManifest] = None
    metrics: Optional[RunMetrics] = None


class RunSummary(BaseModel):
    run_id: str
    created_at: str
    strategy_id: str
    status: str
    symbol: Optional[str] = None
    # Standardized field names (must match frontend RunSummarySchema)
    run_from: Optional[str] = None
    run_to: Optional[str] = None
    duration_ms: Optional[int] = None

