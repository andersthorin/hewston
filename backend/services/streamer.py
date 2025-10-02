from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime as _dt
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import math

import polars as pl
import pandas as pd

from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.constants import DEFAULT_FPS
from backend.domain.types import StreamFrame
from backend.utils.datetime import normalize_timestamp

logger = logging.getLogger(__name__)

def _get_catalog() -> SqliteCatalog:
    # Use default env-based constructor
    return SqliteCatalog()


def _resolve_artifacts(run_id: str) -> Tuple[Dict[str, str], Optional[str]]:
    """Return artifact paths and dataset_id for a run_id."""
    cat = _get_catalog()
    row = cat.get_backtest(run_id)
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
            # Prefer 1Min naming, then legacy 1m, else first bars_*.parquet
            for p in files:
                s = str(p)
                if s.endswith("bars_1Min.parquet"):
                    return p
            for p in files:
                s = str(p)
                if s.endswith("bars_1m.parquet"):
                    return p
            for p in files:
                s = str(p)
                if "/bars_" in s and s.endswith(".parquet"):
                    return p
            return files[0] if files else None
        except Exception:
            return None


def _iter_parquet_dicts(path: str, select: Optional[List[str]] = None) -> List[dict]:
    df = pl.read_parquet(path, columns=select)
    return df.to_dicts()


def _load_bars_data(dataset_id: Optional[str]) -> Dict[int, dict]:
    """Load and normalize bars data into a timestamp-keyed dictionary."""
    bars_map: Dict[int, dict] = {}
    if not dataset_id:
        return bars_map

    bars_path = _resolve_bars_path(dataset_id)
    if not bars_path or not Path(bars_path).exists():
        return bars_map

    # columns: support both new ('t') and legacy ('ts')
    df = pl.read_parquet(bars_path)
    if "ts" not in df.columns and "t" in df.columns:
        df = df.rename({"t": "ts"})

    if "ts" in df.columns:
        for r in df.select(["ts", "o", "h", "l", "c", "v"]).to_dicts():
            key, _ = normalize_timestamp(r["ts"])  # normalize join key only
            bars_map[key] = {
                "o": r.get("o"),
                "h": r.get("h"),
                "l": r.get("l"),
                "c": r.get("c"),
                "v": r.get("v"),
            }
    return bars_map


def _organize_orders_by_timestamp(orders_rows: List[dict]) -> Dict[int, List[dict]]:
    """Organize orders by normalized timestamp for efficient lookup."""
    orders_by_ts: Dict[int, List[dict]] = {}
    for o in orders_rows:
        key, _ = normalize_timestamp(o.get("ts_utc"))
        orders_by_ts.setdefault(key, []).append(o)
    return orders_by_ts


def _normalize_order_timestamps(orders: List[dict]) -> List[dict]:
    """Normalize datetime values in orders to ISO strings for JSON serialization."""
    orders_payload: List[dict] = []
    for o in orders:
        o2 = dict(o)
        # normalize any datetime-like values to ISO strings
        for kk, vv in list(o2.items()):
            try:
                if isinstance(vv, (_dt, pd.Timestamp)):
                    _, iso_v = normalize_timestamp(vv)
                    o2[kk] = iso_v
            except Exception:
                pass
        orders_payload.append(o2)
    return orders_payload


def _calculate_decimation_stride(total_frames: int, fps: int, realtime: bool) -> int:
    """Calculate the stride for frame decimation based on total frames and target FPS."""
    if realtime:
        target = fps  # logical target; we stride if needed
        return max(1, total_frames // target) if total_frames > target else 1
    else:
        # Option A: no decimation in non-realtime mode — emit all frames
        return 1


def _precompute_metrics_from_equity(equity_rows: List[dict]) -> Dict[str, List[Optional[float]]]:
    """Compute per-index running metrics for finished runs.
    Returns dict of arrays aligned to equity_rows order with possible None entries.
    Metrics:
      - total_return_so_far: equity[i]/equity[0] - 1
      - max_drawdown_so_far: max_{tau<=i} (peak_to_date - equity[tau]) / peak_to_date
      - sharpe_so_far: mean(r[1..i]) / std(r[1..i]) with r_t = equity[t]/equity[t-1]-1, r_f=0 (no annualization)
    """
    n = len(equity_rows)
    if n == 0:
        return {"total_return_so_far": [], "max_drawdown_so_far": [], "sharpe_so_far": []}

    vals = [float(er.get("value", float("nan"))) for er in equity_rows]
    base = vals[0]

    trs: List[Optional[float]] = [None] * n
    mdd: List[Optional[float]] = [None] * n
    shp: List[Optional[float]] = [None] * n

    # total return so far
    for i in range(n):
        v = vals[i]
        if base and base != 0.0 and math.isfinite(v):
            trs[i] = (v / base) - 1.0
        else:
            trs[i] = None

    # max drawdown so far
    peak = -float("inf")
    cur_mdd = 0.0
    for i in range(n):
        v = vals[i]
        if math.isfinite(v):
            if v > peak:
                peak = v
            if peak and peak > 0.0:
                dd = (peak - v) / peak
                if dd > cur_mdd:
                    cur_mdd = dd
                mdd[i] = cur_mdd
            else:
                mdd[i] = None
        else:
            mdd[i] = None

    # sharpe so far (run-to-date, r_f=0, no annualization)
    sum_r = 0.0
    sum_r2 = 0.0
    count = 0
    prev = vals[0]
    shp[0] = None
    for i in range(1, n):
        v = vals[i]
        if math.isfinite(v) and math.isfinite(prev) and prev != 0.0:
            r = (v / prev) - 1.0
            sum_r += r
            sum_r2 += r * r
            count += 1
            mean = sum_r / count
            var = (sum_r2 / count) - (mean * mean)
            std = math.sqrt(var) if var > 0 else 0.0
            if std > 0:
                shp[i] = mean / std
            else:
                shp[i] = None
        else:
            shp[i] = None
        prev = v

    return {
        "total_return_so_far": trs,
        "max_drawdown_so_far": mdd,
        "sharpe_so_far": shp,
    }



async def produce_frames(
    *,
    run_id: str,
    fps: int = DEFAULT_FPS,
    speed: float = 1.0,
    realtime: bool = False,
) -> AsyncGenerator[StreamFrame, None]:
    """
    Async generator producing StreamFrame from run artifacts, decimated to ~fps.
    - If realtime=True, sleeps between frames according to fps and speed; else yields as fast as possible (test mode).
    - Decimation: selects approximately ceil(N / max_frames) stride.
    """
    # Load and validate artifacts
    artifacts, dataset_id = _resolve_artifacts(run_id)
    if not artifacts.get("equity") or not artifacts.get("orders"):
        raise FileNotFoundError("missing artifacts")

    # Load data from parquet files
    equity_rows = _iter_parquet_dicts(artifacts["equity"], select=["ts_utc", "value"]) if artifacts.get("equity") else []
    orders_rows = _iter_parquet_dicts(artifacts["orders"]) if artifacts.get("orders") else []

    # Precompute metrics from equity for finished runs
    metrics_arrays = _precompute_metrics_from_equity(equity_rows)

    # Prepare data structures
    bars_map = _load_bars_data(dataset_id)
    orders_by_ts = _organize_orders_by_timestamp(orders_rows)

    total = len(equity_rows)
    if total == 0:
        return
    # Decimation stride
    if realtime:
        target = fps  # logical target; we stride if needed
        stride = max(1, total // target) if total > target else 1
    else:
        # Option A: no decimation in non-realtime mode — emit all frames
        stride = 1

    dropped = 0
    produced = 0
    # Produce frames
    try:
        for i in range(0, total, stride):
            er = equity_rows[i]
            key, iso = normalize_timestamp(er["ts_utc"])
            ohlc = bars_map.get(key)
            # normalize orders to JSON-serializable (ts_utc -> ISO string)
            orders_payload: List[dict] = []
            for o in orders_by_ts.get(key, []) or []:
                o2 = dict(o)
                # normalize any datetime-like values to ISO strings
                for kk, vv in list(o2.items()):
                    try:
                        if isinstance(vv, (_dt, pd.Timestamp)):
                            _, iso_v = normalize_timestamp(vv)
                            o2[kk] = iso_v
                    except Exception:
                        pass
                orders_payload.append(o2)
            # Metrics attachment for this index (may contain None values)
            mi = {
                "total_return_so_far": metrics_arrays.get("total_return_so_far", [None]*total)[i],
                "max_drawdown_so_far": metrics_arrays.get("max_drawdown_so_far", [None]*total)[i],
                "sharpe_so_far": metrics_arrays.get("sharpe_so_far", [None]*total)[i],
            }
            frame = StreamFrame(
                t="frame",
                ts=iso,
                ohlc=ohlc,
                orders=orders_payload,
                equity={"ts": iso, "value": er["value"]},
                metrics=mi,
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

