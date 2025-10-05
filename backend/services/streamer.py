from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime as _dt
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import math

import time
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




def _select_hourly_indices(equity_rows: List[dict], rth_only: bool = False) -> List[int]:
    """Return indices of the last equity point within each UTC hour.
    Optionally filter to Regular Trading Hours (RTH) in America/New_York (09:30–16:00), Mon–Fri.
    Uses epoch seconds from normalize_timestamp(ts_utc) to bucket by hour.
    """
    hour_to_idx: Dict[int, int] = {}

    def _is_rth(epoch_sec: int) -> bool:
        if not rth_only:
            return True
        try:
            from datetime import datetime, timezone
            try:
                from zoneinfo import ZoneInfo  # Python 3.9+
            except Exception:
                # Fallback: treat as always RTH if zoneinfo missing
                return True
            dt_utc = _dt.fromtimestamp(epoch_sec, tz=_dt.timezone.utc) if hasattr(_dt, 'timezone') else datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
            ny = dt_utc.astimezone(ZoneInfo("America/New_York"))
            # Weekday 0=Mon..4=Fri
            if ny.weekday() > 4:
                return False
            h, m = ny.hour, ny.minute
            # RTH: 09:30 <= time < 16:00 local
            if h < 9 or h > 15:
                # allow 9:30+ and any 10..15; exclude 16:xx
                return (h == 9 and m >= 30) if h == 9 else False
            if h == 9:
                return m >= 30
            return True
        except Exception:
            return True

    for i, er in enumerate(equity_rows):
        try:
            epoch, _ = normalize_timestamp(er.get("ts_utc"))
            if not _is_rth(int(epoch)):
                continue
            hour_bucket = int(epoch) // 3600
            # Keep last index encountered for this hour
            hour_to_idx[hour_bucket] = i
        except Exception:
            # Skip rows with invalid timestamps
            continue
    # Return indices ordered by hour
    return [hour_to_idx[h] for h in sorted(hour_to_idx.keys())]


async def produce_frames(
    *,
    run_id: str,
    fps: int = DEFAULT_FPS,
    speed: float = 1.0,
    realtime: bool = False,
    cadence: str = "1m",
    rth_only: bool = True,
) -> AsyncGenerator[StreamFrame, None]:
    """
    Async generator producing StreamFrame from run artifacts, optionally resampled to cadence, with optional RTH-only filtering, and paced to ~fps.
    - cadence: "1m" (default) emits every equity point; "1h" emits last point per UTC hour.
    - rth_only: when True, include only points within 09:30-16:00 America/New_York, Mon-Fri.
    - If realtime=True, sleeps between frames according to fps and speed; else yields as fast as possible (test mode).
    """
    # Load and validate artifacts
    artifacts, dataset_id = _resolve_artifacts(run_id)
    if not artifacts.get("equity") or not artifacts.get("orders"):
        raise FileNotFoundError("missing artifacts")

    # Load data from parquet files
    equity_rows = _iter_parquet_dicts(artifacts["equity"], select=["ts_utc", "value"]) if artifacts.get("equity") else []
    orders_rows = _iter_parquet_dicts(artifacts["orders"]) if artifacts.get("orders") else []

    # Precompute basic metrics from equity for finished runs (fallback; Sharpe not annualized)
    metrics_arrays = _precompute_metrics_from_equity(equity_rows)

    # Load metrics artifact (optional) for precomputed cumulative metrics series
    metrics_lookup: List[Tuple[int, dict]] = []
    try:
        mpath = artifacts.get("metrics")
        if mpath and Path(mpath).exists():
            with open(mpath, "r") as f:
                mj = json.load(f)
            # Expect series as [[iso, {..metrics..}], ...]
            series_items = mj.get("series") or []
            for item in series_items:
                try:
                    if isinstance(item, list) and len(item) >= 2:
                        epoch, _ = normalize_timestamp(item[0])
                        metrics_obj = item[1] if isinstance(item[1], dict) else {}
                        metrics_lookup.append((int(epoch), metrics_obj))
                    elif isinstance(item, dict) and "ts" in item:
                        epoch, _ = normalize_timestamp(item.get("ts"))
                        metrics_obj = item.get("metrics", {}) or {}
                        metrics_lookup.append((int(epoch), metrics_obj))
                except Exception:
                    continue
            metrics_lookup.sort(key=lambda x: x[0])
    except Exception:
        metrics_lookup = []

    # Prepare data structures
    bars_map = _load_bars_data(dataset_id)
    orders_by_ts = _organize_orders_by_timestamp(orders_rows)

    # Determine indices to emit based on cadence
    n_equity = len(equity_rows)
    if cadence == "1h":
        indices = _select_hourly_indices(equity_rows, rth_only=rth_only)
    else:
        indices = list(range(n_equity))

    total = len(indices)
    if total == 0:
        return

    # Decimation stride (applied on selected indices)
    # In realtime mode we pace using asyncio.sleep per frame; do not decimate based on total.
    # Always emit all selected frames in order.
    stride = 1

    dropped = 0
    produced = 0
    # TEMP DEBUG: limit logging of first 20 produced frames per run
    debug_count = 0
    last_emit = 0.0


    # Produce frames
    try:
        for pos in range(0, total, stride):
            i = indices[pos]
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
            # Prefer precomputed metrics if available; otherwise fallback to on-the-fly estimates
            if 'm_idx' not in locals():
                m_idx = -1
                last_metrics = None
            if metrics_lookup:
                while (m_idx + 1) < len(metrics_lookup) and metrics_lookup[m_idx + 1][0] <= key:
                    last_metrics = metrics_lookup[m_idx + 1][1]
                    m_idx += 1
                mi = last_metrics or {}
            else:
                # Fallback path (legacy): compute minimal metrics from equity
                r_cur = None
                try:
                    v_cur = float(er["value"])
                    if 'prev_equity_val' not in locals():
                        prev_equity_val = v_cur
                    if prev_equity_val and prev_equity_val != 0.0:
                        r_cur = (v_cur / prev_equity_val) - 1.0
                    prev_equity_val = v_cur
                except Exception:
                    pass

                # Annualize Sharpe from fallback computation assuming 1-minute bars (P = 252*390)
                P = 252 * 390
                shp_raw = metrics_arrays.get("sharpe_so_far", [None]*n_equity)[i]
                shp_ann = (math.sqrt(P) * shp_raw) if (isinstance(shp_raw, float) or isinstance(shp_raw, int)) and shp_raw is not None else (math.sqrt(P) * shp_raw if shp_raw is not None else None)

                mi = {
                    "return": r_cur,
                    "realized_pnl": None,
                    "total_return": metrics_arrays.get("total_return_so_far", [None]*n_equity)[i],
                    "drawdown": metrics_arrays.get("max_drawdown_so_far", [None]*n_equity)[i],
                    "sharpe": shp_ann,
                    "win_rate": None,
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
            # Include total_frames on the first emitted frame for UI progress
            if produced == 0:
                try:
                    # dataclass has optional field; attach if available
                    frame.total_frames = total  # type: ignore[attr-defined]
                except Exception:
                    pass

            # Diagnostics: backend emit delta
            try:
                now = time.perf_counter()
                dt_ms = (now - last_emit) * 1000.0 if last_emit > 0.0 else 0.0
                last_emit = now
                logger.info("diag.backend.emit", extra={"run_id": run_id, "dt_ms": round(dt_ms, 2), "ts": iso})
            except Exception:
                pass
            # TEMP DEBUG: log first 20 backend frames with ts and equity
            if debug_count < 20:
                try:
                    logger.info(
                        f"TEMP_DEBUG.backend.frame run_id={run_id} n={debug_count + 1} ts={iso} eq={float(er['value'])}"
                    )
                except Exception:
                    pass
                debug_count += 1
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

