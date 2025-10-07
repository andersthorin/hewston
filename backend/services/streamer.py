from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from collections.abc import AsyncGenerator
from datetime import UTC

from datetime import datetime as _dt
from pathlib import Path

import pandas as pd
import polars as pl

from backend.constants import DEFAULT_FPS
from backend.domain.types import StreamFrame
from backend.ports.catalog import CatalogPort
from backend.utils.datetime import normalize_timestamp

logger = logging.getLogger(__name__)


def _get_catalog() -> CatalogPort:
    """Return a CatalogPort without static dependency on adapters."""
    import importlib
    module = importlib.import_module("backend.adapters.sqlite_catalog")
    SqliteCatalog = getattr(module, "SqliteCatalog")
    return SqliteCatalog()  # type: ignore[return-value]


def _resolve_artifacts(run_id: str) -> tuple[dict[str, str], str | None]:
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


def _resolve_bars_path(dataset_id: str) -> str | None:
    cat = _get_catalog()
    with cat._connect() as conn:  # type: ignore[attr-defined]
        r = conn.execute(
            "SELECT bars_parquet_json FROM datasets WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()
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


def _iter_parquet_dicts(path: str, select: list[str] | None = None) -> list[dict]:
    df = pl.read_parquet(path, columns=select)
    return df.to_dicts()


def _load_bars_data(dataset_id: str | None) -> dict[int, dict]:
    """Load and normalize bars data into a timestamp-keyed dictionary."""
    bars_map: dict[int, dict] = {}
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


def _organize_orders_by_timestamp(orders_rows: list[dict]) -> dict[int, list[dict]]:
    """Organize orders by normalized timestamp for efficient lookup."""
    orders_by_ts: dict[int, list[dict]] = {}
    for o in orders_rows:
        key, _ = normalize_timestamp(o.get("ts_utc"))
        orders_by_ts.setdefault(key, []).append(o)
    return orders_by_ts


def _normalize_order_timestamps(orders: list[dict]) -> list[dict]:
    """Normalize datetime values in orders to ISO strings for JSON serialization."""
    orders_payload: list[dict] = []
    for o in orders:
        o2 = dict(o)
        # normalize any datetime-like values to ISO strings
        for kk, vv in list(o2.items()):
            try:
                if isinstance(vv, _dt | pd.Timestamp):
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


def _compute_total_return_series(vals: list[float]) -> list[float | None]:
    n = len(vals)
    if n == 0:
        return []
    base = vals[0]
    trs: list[float | None] = [None] * n
    for i, v in enumerate(vals):
        if base and base != 0.0 and math.isfinite(v):
            trs[i] = (v / base) - 1.0
        else:
            trs[i] = None
    return trs


def _compute_max_drawdown_series(vals: list[float]) -> list[float | None]:
    n = len(vals)
    mdd: list[float | None] = [None] * n
    peak = -float("inf")
    cur_mdd = 0.0
    for i, v in enumerate(vals):
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
    return mdd


def _compute_running_sharpe_series(vals: list[float]) -> list[float | None]:
    n = len(vals)
    if n == 0:
        return []
    shp: list[float | None] = [None] * n
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
            shp[i] = (mean / std) if std > 0 else None
        else:
            shp[i] = None
        prev = v
    return shp


def _precompute_metrics_from_equity(equity_rows: list[dict]) -> dict[str, list[float | None]]:
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

    trs = _compute_total_return_series(vals)
    mdd = _compute_max_drawdown_series(vals)
    shp = _compute_running_sharpe_series(vals)

    return {
        "total_return_so_far": trs,
        "max_drawdown_so_far": mdd,
        "sharpe_so_far": shp,
    }


def _is_rth_epoch(epoch_sec: int, *, include_close: bool = False) -> bool:
    """Return True if epoch_sec is within RTH (America/New_York).
    include_close=True allows exactly 16:00:00, but excludes >16:00.
    On tz errors, conservatively return True to avoid over-filtering.
    """
    try:
        from zoneinfo import ZoneInfo  # type: ignore

        dt_utc = _dt.fromtimestamp(epoch_sec, tz=UTC)
        ny = dt_utc.astimezone(ZoneInfo("America/New_York"))
        if ny.weekday() > 4:
            return False
        h, m = ny.hour, ny.minute
        # Start: 09:30+
        if h < 9 or (h == 9 and m < 30):
            return False
        # End: < 16:00, or ==16:00 if include_close
        if h < 16:
            return True
        if h > 16:
            return False
        # h == 16
        return include_close and m == 0
    except Exception:
        return True


def _ny_date_key(epoch_sec: int) -> str:
    """Return ISO date string for America/New_York; fallback to UTC on errors."""
    try:
        from zoneinfo import ZoneInfo  # type: ignore

        dt_utc = _dt.fromtimestamp(epoch_sec, tz=UTC)
        return dt_utc.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return _dt.fromtimestamp(epoch_sec, tz=UTC).date().isoformat()


def _hour_bucket(epoch_sec: int) -> int:
    return int(epoch_sec) // 3600


def _select_hourly_indices(equity_rows: list[dict], rth_only: bool = False) -> list[int]:
    """Return indices of the last equity point within each UTC hour.
    Optionally filter to Regular Trading Hours (RTH) in America/New_York (09:30–16:00), Mon–Fri.
    Uses epoch seconds from normalize_timestamp(ts_utc) to bucket by hour.
    """
    hour_to_idx: dict[int, int] = {}

    for i, er in enumerate(equity_rows):
        try:
            epoch, _ = normalize_timestamp(er.get("ts_utc"))
            epoch_i = int(epoch)
            if rth_only and not _is_rth_epoch(epoch_i):
                continue
            # Keep last index encountered for this hour
            hour_to_idx[_hour_bucket(epoch_i)] = i
        except Exception:
            continue
    return [hour_to_idx[h] for h in sorted(hour_to_idx.keys())]


def _select_daily_close_indices(equity_rows: list[dict], rth_only: bool = True) -> list[int]:
    """Return indices of the last equity point for each trading day (America/New_York),
    using Regular Trading Hours (RTH) 09:30–16:00 if rth_only=True.
    The "daily close" is treated as the last equity observation within RTH for that local day.
    """
    day_to_idx: dict[str, int] = {}

    for i, er in enumerate(equity_rows):
        try:
            epoch, _ = normalize_timestamp(er.get("ts_utc"))
            epoch_i = int(epoch)
            # Only consider RTH points if required
            if rth_only and not _is_rth_epoch(epoch_i, include_close=True):
                continue
            day_key = _ny_date_key(epoch_i)
            # Keep last index encountered for the trading day within RTH
            day_to_idx[day_key] = i
        except Exception:
            continue

    return [day_to_idx[k] for k in sorted(day_to_idx.keys())]


def _compute_daily_return_series_aligned(
    equity_rows: list[dict], daily_close_indices: list[int]
) -> list[float | None]:
    """Compute simple daily close-to-close returns aligned to each equity index.
    For indices up to a daily close, fill with that day's close-to-close return.
    Between close days, the last completed daily return is propagated.
    """
    n = len(equity_rows)
    daily_ret_by_idx: list[float | None] = [None] * n
    if n == 0 or not daily_close_indices:
        return daily_ret_by_idx

    prev_close_val: float | None = None
    prev_close_idx: int | None = None

    for di in daily_close_indices:
        try:
            v = float(equity_rows[di].get("value", float("nan")))
        except Exception:
            v = float("nan")
        r: float | None = None
        if (
            prev_close_val is not None
            and math.isfinite(prev_close_val)
            and prev_close_val != 0.0
            and math.isfinite(v)
        ):
            r = (v / prev_close_val) - 1.0
        # Fill from previous close (exclusive) up to this close (inclusive)
        start = (prev_close_idx + 1) if prev_close_idx is not None else 0
        for i in range(start, di + 1):
            daily_ret_by_idx[i] = r
        prev_close_val = v
        prev_close_idx = di

    # Propagate last known daily return to the end
    if prev_close_idx is not None:
        last_val = daily_ret_by_idx[prev_close_idx]
        for i in range(prev_close_idx + 1, n):
            daily_ret_by_idx[i] = last_val

    return daily_ret_by_idx


def _compute_daily_sharpe_series_aligned(
    equity_rows: list[dict], daily_close_indices: list[int]
) -> list[float | None]:
    """Compute daily Sharpe-so-far (annualized with sqrt(252)) and align to each equity index.
    For any minute index between two daily closes, we use the Sharpe computed up to the last
    completed daily close.
    """
    n = len(equity_rows)
    sharpe_ann_by_idx: list[float | None] = [None] * n
    if n == 0 or not daily_close_indices:
        return sharpe_ann_by_idx

    sum_r = 0.0
    sum_r2 = 0.0
    count = 0
    prev_close_val: float | None = None
    prev_close_idx: int | None = None

    for di in daily_close_indices:
        try:
            v = float(equity_rows[di].get("value", float("nan")))
        except Exception:
            v = float("nan")
        # compute simple daily return from last close
        if (
            prev_close_val is not None
            and math.isfinite(prev_close_val)
            and prev_close_val != 0.0
            and math.isfinite(v)
        ):
            r = (v / prev_close_val) - 1.0
            sum_r += r
            sum_r2 += r * r
            count += 1
        prev_close_val = v

        sharpe_rt: float | None = None
        if count >= 2:
            mean = sum_r / count
            var = (sum_r2 / count) - (mean * mean)
            std = math.sqrt(var) if var > 0 else 0.0
            if std > 0:
                sharpe_rt = mean / std
        sharpe_ann = math.sqrt(252) * sharpe_rt if sharpe_rt is not None else None

        # Fill aligned values from previous close idx (exclusive) up to this close idx (inclusive)
        start = (prev_close_idx + 1) if prev_close_idx is not None else 0
        for i in range(start, di + 1):
            sharpe_ann_by_idx[i] = sharpe_ann
        prev_close_idx = di

    # Propagate last known Sharpe to the end
    if prev_close_idx is not None:
        last_val = sharpe_ann_by_idx[prev_close_idx]
        for i in range(prev_close_idx + 1, n):
            sharpe_ann_by_idx[i] = last_val

    return sharpe_ann_by_idx


def _normalize_orders_payload(orders_by_ts: dict[int, list[dict]], key: int) -> list[dict]:
    orders_payload: list[dict] = []
    for o in orders_by_ts.get(key, []) or []:
        o2 = dict(o)
        for kk, vv in list(o2.items()):
            try:
                if isinstance(vv, _dt | pd.Timestamp):
                    _, iso_v = normalize_timestamp(vv)
                    o2[kk] = iso_v
            except Exception:
                pass
        orders_payload.append(o2)
    return orders_payload


def _complete_metrics(
    mi: dict,
    i: int,
    n_equity: int,
    metrics_arrays: dict,
    daily_sharpe_ann_by_index: list,
    daily_return_by_index: list,
    annualization_P: float | None,
    r_cur: float | None,
) -> dict:
    # Fill return only if not present (preserve precomputed None)
    if "return" not in mi:
        daily_r = daily_return_by_index[i] if i < len(daily_return_by_index) else None
        mi["return"] = daily_r if daily_r is not None else r_cur

    # total_return / drawdown from arrays
    if ("total_return" not in mi) or (mi.get("total_return") is None):
        mi["total_return"] = metrics_arrays.get("total_return_so_far", [None] * n_equity)[i]
    if ("drawdown" not in mi) or (mi.get("drawdown") is None):
        mi["drawdown"] = metrics_arrays.get("max_drawdown_so_far", [None] * n_equity)[i]

    # Sharpe: prefer daily aligned; fallback to running Sharpe; annualize if P provided
    if ("sharpe" not in mi) or (mi.get("sharpe") is None):
        shp_daily = daily_sharpe_ann_by_index[i] if i < len(daily_sharpe_ann_by_index) else None
        if shp_daily is not None:
            mi["sharpe"] = shp_daily
        else:
            shp_rt = metrics_arrays.get("sharpe_so_far", [None] * n_equity)[i]
            try:
                if shp_rt is not None and annualization_P and annualization_P > 0:
                    import math as _math

                    mi["sharpe"] = shp_rt * (_math.sqrt(float(annualization_P)))
                else:
                    mi["sharpe"] = shp_rt
            except Exception:
                mi["sharpe"] = shp_rt
    return mi


def _load_metrics_artifact(
    artifacts: dict[str, str]
) -> tuple[list[tuple[int, dict]], float | None]:
    metrics_lookup: list[tuple[int, dict]] = []
    annualization_P: float | None = None
    try:
        mpath = artifacts.get("metrics")
        if mpath and Path(mpath).exists():
            with open(mpath) as f:
                mj = json.load(f)
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
            try:
                v = mj.get("annualization_P")
                annualization_P = float(v) if v is not None else None
            except Exception:
                annualization_P = None
    except Exception:
        return [], None
    return metrics_lookup, annualization_P


def _advance_metrics_cursor(
    metrics_lookup: list[tuple[int, dict]], m_idx: int, key: int, last_metrics: dict | None
) -> tuple[int, dict | None]:
    """Advance metrics cursor so that last_metrics is the latest metrics with ts <= key."""
    if not metrics_lookup:
        return m_idx, last_metrics
    while (m_idx + 1) < len(metrics_lookup) and metrics_lookup[m_idx + 1][0] <= key:
        last_metrics = metrics_lookup[m_idx + 1][1]
        m_idx += 1
    return m_idx, last_metrics


def _compute_r_cur(prev_equity_val: float | None, v_cur: float) -> tuple[float | None, float]:
    """Compute per-frame return and updated prev equity value, preserving None when not computable."""
    if prev_equity_val is None:
        return None, v_cur
    if prev_equity_val != 0.0:
        return (v_cur / prev_equity_val) - 1.0, v_cur
    return None, v_cur


def _log_backend_emit(logger, run_id: str, iso: str, last_emit: float) -> float:
    """Log backend emit diagnostics and return updated last_emit timestamp."""
    try:
        now = time.perf_counter()
        dt_ms = (now - last_emit) * 1000.0 if last_emit > 0.0 else 0.0
        logger.info(
            "diag.backend.emit",
            extra={"run_id": run_id, "dt_ms": round(dt_ms, 2), "ts": iso},
        )
        return now
    except Exception:
        return last_emit


def _log_temp_debug(logger, run_id: str, debug_count: int, er: dict, iso: str) -> int:
    """Log first 20 frames for local debugging; return updated debug_count."""
    if debug_count < 20:
        try:
            logger.info(
                f"TEMP_DEBUG.backend.frame run_id={run_id} n={debug_count + 1} ts={iso} eq={float(er['value'])}"
            )
        except Exception:
            pass
        return debug_count + 1
    return debug_count


def _compute_frame_metrics(
    i: int,
    er: dict,
    *,
    metrics_lookup: list[tuple[int, dict]] | None,
    m_idx: int | None,
    last_metrics: dict | None,
    prev_equity_val: float | None,
    n_equity: int,
    metrics_arrays: dict,
    daily_sharpe_ann_by_index: list,
    daily_return_by_index: list,
    annualization_P: float | None,
) -> tuple[dict, int, dict | None, float | None]:
    """Return (metrics, m_idx, last_metrics, prev_equity_val) for current equity row."""
    if metrics_lookup:
        m_idx = -1 if m_idx is None else m_idx
        m_idx, last_metrics = _advance_metrics_cursor(
            metrics_lookup, m_idx, normalize_timestamp(er["ts_utc"])[0], last_metrics
        )
        mi = dict(last_metrics or {})
    else:
        mi = {}
    # Compute per-frame return (fallback) and prefer aligned daily return
    r_cur = None
    try:
        v_cur = float(er["value"])
        r_cur, prev_equity_val = _compute_r_cur(prev_equity_val, v_cur)
    except Exception:
        pass
    mi = _complete_metrics(
        mi,
        i,
        n_equity,
        metrics_arrays,
        daily_sharpe_ann_by_index,
        daily_return_by_index,
        annualization_P,
        r_cur,
    )
    if not metrics_lookup:
        mi.setdefault("realized_pnl", None)
        mi.setdefault("win_rate", None)
    return mi, (m_idx or -1), last_metrics, prev_equity_val


def _attach_total_frames(frame: StreamFrame, produced: int, total: int) -> None:
    if produced == 0:
        try:
            frame.total_frames = total  # type: ignore[attr-defined]
        except Exception:
            pass


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
    equity_rows = (
        _iter_parquet_dicts(artifacts["equity"], select=["ts_utc", "value"])
        if artifacts.get("equity")
        else []
    )
    orders_rows = _iter_parquet_dicts(artifacts["orders"]) if artifacts.get("orders") else []

    # Precompute basic metrics from equity for finished runs (fallback; Sharpe not annualized)
    metrics_arrays = _precompute_metrics_from_equity(equity_rows)

    # Load metrics artifact (optional) for precomputed cumulative metrics series
    metrics_lookup, annualization_P = _load_metrics_artifact(artifacts)

    # Prepare data structures
    bars_map = _load_bars_data(dataset_id)
    orders_by_ts = _organize_orders_by_timestamp(orders_rows)

    # Precompute daily series aligned to index
    try:
        daily_close_indices = _select_daily_close_indices(equity_rows, rth_only=rth_only)
        daily_sharpe_ann_by_index = _compute_daily_sharpe_series_aligned(
            equity_rows, daily_close_indices
        )
        daily_return_by_index = _compute_daily_return_series_aligned(
            equity_rows, daily_close_indices
        )
    except Exception:
        daily_sharpe_ann_by_index = [None] * len(equity_rows)
        daily_return_by_index = [None] * len(equity_rows)

    # Determine indices to emit based on cadence
    n_equity = len(equity_rows)
    if cadence == "1h":
        indices = _select_hourly_indices(equity_rows, rth_only=rth_only)
    else:
        indices = list(range(n_equity))

    # Always ensure the very last equity point is included as the final frame
    if n_equity > 0 and (len(indices) == 0 or indices[-1] != (n_equity - 1)):
        indices = list(indices) + [n_equity - 1]

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
            orders_payload = _normalize_orders_payload(orders_by_ts, key)
            # Prefer precomputed metrics if available; otherwise fallback to on-the-fly estimates
            if "m_idx" not in locals():
                m_idx = -1
                last_metrics = None
            mi, m_idx, last_metrics, prev_equity_val = _compute_frame_metrics(
                i,
                er,
                metrics_lookup=metrics_lookup,
                m_idx=locals().get("m_idx"),
                last_metrics=locals().get("last_metrics"),
                prev_equity_val=locals().get("prev_equity_val"),
                n_equity=n_equity,
                metrics_arrays=metrics_arrays,
                daily_sharpe_ann_by_index=daily_sharpe_ann_by_index,
                daily_return_by_index=daily_return_by_index,
                annualization_P=annualization_P,
            )
            frame = StreamFrame(
                t="frame",
                ts=iso,
                ohlc=ohlc,
                orders=orders_payload,
                equity={"ts": iso, "value": er["value"]},
                metrics=mi,
                dropped=dropped,
            )
            _attach_total_frames(frame, produced, total)

            # Diagnostics: backend emit delta
            last_emit = _log_backend_emit(logger, run_id, iso, last_emit)
            # TEMP DEBUG: log first 20 backend frames with ts and equity
            debug_count = _log_temp_debug(logger, run_id, debug_count, er, iso)
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
