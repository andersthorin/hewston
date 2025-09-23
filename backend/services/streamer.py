from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import polars as pl

from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.domain.types import StreamFrame

logger = logging.getLogger(__name__)

def _get_catalog() -> SqliteCatalog:
    # Use default env-based constructor
    return SqliteCatalog()


def _resolve_artifacts(run_id: str) -> Tuple[Dict[str, str], Optional[str]]:
    """Return artifact paths and dataset_id for a run_id."""
    cat = _get_catalog()
    row = cat.get_run(run_id)
    if not row:
        raise FileNotFoundError(f"run not found: {run_id}")
    arts = row["artifacts"]
    dsid = row.get("dataset_id")
    return {
        "equity": arts.get("equity_path"),
        "orders": arts.get("orders_path"),
        "fills": arts.get("fills_path"),
        "metrics": arts.get("metrics_path"),
    }, dsid


def _resolve_bars_path(dataset_id: str) -> Optional[str]:
    import sqlite3

    cat = _get_catalog()
    with cat._connect() as conn:  # type: ignore[attr-defined]
        r = conn.execute("SELECT bars_parquet_json FROM datasets WHERE dataset_id = ?", (dataset_id,)).fetchone()
        if not r:
            return None
        try:
            files = json.loads(r[0])
            for p in files:
                if str(p).endswith("bars_1m.parquet"):
                    return p
            return files[0] if files else None
        except Exception:
            return None


def _iter_parquet_dicts(path: str, select: Optional[List[str]] = None) -> List[dict]:
    df = pl.read_parquet(path, columns=select)
    return df.to_dicts()


async def produce_frames(
    *,
    run_id: str,
    fps: int = 30,
    speed: float = 1.0,
    realtime: bool = False,
) -> AsyncGenerator[StreamFrame, None]:
    """
    Async generator producing StreamFrame from run artifacts, decimated to ~fps.
    - If realtime=True, sleeps between frames according to fps and speed; else yields as fast as possible (test mode).
    - Decimation: selects approximately ceil(N / max_frames) stride.
    """
    artifacts, dataset_id = _resolve_artifacts(run_id)
    if not artifacts.get("equity") or not artifacts.get("orders"):
        raise FileNotFoundError("missing artifacts")

    equity_rows = _iter_parquet_dicts(artifacts["equity"], select=["ts_utc", "value"]) if artifacts.get("equity") else []
    orders_rows = _iter_parquet_dicts(artifacts["orders"]) if artifacts.get("orders") else []

    bars_map: Dict[str, dict] = {}
    if dataset_id:
        bars_path = _resolve_bars_path(dataset_id)
        if bars_path and Path(bars_path).exists():
            # columns: ts,o,h,l,c,v (from our derive stub)
            for r in _iter_parquet_dicts(bars_path, select=["ts", "o", "h", "l", "c", "v"]):
                bars_map[str(r["ts"])] = {
                    "o": r.get("o"),
                    "h": r.get("h"),
                    "l": r.get("l"),
                    "c": r.get("c"),
                    "v": r.get("v"),
                }

    # Align orders by ts
    orders_by_ts: Dict[str, List[dict]] = {}
    for o in orders_rows:
        ts = str(o.get("ts_utc"))
        orders_by_ts.setdefault(ts, []).append(o)

    total = len(equity_rows)
    if total == 0:
        return
    # Decimation stride
    max_frames = max(1, total)  # with realtime, time-based; here index-based
    target = fps  # logical target; we stride if needed
    stride = max(1, total // target) if total > target else 1

    dropped = 0
    produced = 0
    # Produce frames
    try:
        for i in range(0, total, stride):
            er = equity_rows[i]
            ts = str(er["ts_utc"])
            ohlc = bars_map.get(ts)
            orders = orders_by_ts.get(ts, [])
            frame = StreamFrame(
                t="frame",
                ts=ts,
                ohlc=ohlc,
                orders=orders,
                equity={"ts": ts, "value": er["value"]},
                dropped=dropped,
            )
            yield frame
            produced += 1
            if realtime:
                await asyncio.sleep(max(0.0, (1.0 / float(fps)) / max(1.0, speed)))
    finally:
        # Log a summary for operability (local)
        try:
            logger.info(
                "stream.summary",
                extra={
                    "run_id": run_id,
                    "frames_total_rows": total,
                    "frames_stride": stride,
                    "frames_produced": produced,
                    "frames_dropped_est": max(0, total - produced),
                },
            )
        except Exception:
            pass

