"""Bars API routes for daily, hourly, and minute OHLCV from warehouse."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()


def _base_dir() -> Path:
    return Path(os.getenv("HEWSTON_DATA_DIR", "data")).resolve()


def _isoz(ts: datetime | str | None) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    try:
        return datetime.fromtimestamp(ts.timestamp(), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        try:
            return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None


def _parse_iso_date_range(from_date: str | None, to_date: str | None) -> tuple[datetime, datetime]:
    try:
        ts_from = datetime.fromisoformat((from_date or "1970-01-01") + "T00:00:00+00:00")
        ts_to = datetime.fromisoformat((to_date or "2100-01-01") + "T23:59:59+00:00")
        return ts_from, ts_to
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid from/to format; expected YYYY-MM-DD",
        ) from e


def _list_dates_1h(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted(
        [p.name.split("=")[1] for p in base.glob("date=*") if p.is_dir() and "=" in p.name]
    )


def _paths_1h_for_range(base: Path, ts_from: datetime, ts_to: datetime) -> list[str]:
    if not base.exists():
        return []
    out: list[str] = []
    d = ts_from.date()
    while d <= ts_to.date():
        p = base / f"date={d}" / "bars.parquet"
        if p.exists():
            out.append(str(p))
        d = (datetime.combine(d, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)).date()
    return out


@router.get("/bars/daily")
async def get_daily(
    symbol: str,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
):
    """Return daily OHLCV derived from pre-aggregated 1-hour warehouse bars.

    Bounds by available dates if from/to are omitted.
    """
    # Build list of warehouse paths (prefer 1h pre-aggregated)
    ts_from, ts_to = _parse_iso_date_range(from_date, to_date)

    base_1h = _base_dir() / "warehouse" / "bars" / "mid_1h" / "venue=XNAS" / f"symbol={symbol}"

    # If no explicit range provided, bound by available dates in warehouse
    if (from_date is None) and (to_date is None):
        ds = _list_dates_1h(base_1h)
        if not ds:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No 1-hour warehouse data available for {symbol}. "
                    f"Run warehouse backfill first."
                ),
            )
        ts_from = datetime.fromisoformat(ds[0] + "T00:00:00+00:00")
        ts_to = datetime.fromisoformat(ds[-1] + "T23:59:59+00:00")

    paths_1h = _paths_1h_for_range(base_1h, ts_from, ts_to)
    if not paths_1h:
        _from = from_date or ts_from.date().isoformat()
        _to = to_date or ts_to.date().isoformat()
        raise HTTPException(
            status_code=404,
            detail=(
                f"No 1-hour warehouse data available for {symbol} in date range {_from} to {_to}. "
                "Run warehouse backfill first."
            ),
        )

    q = pl.scan_parquet(paths_1h).filter(
        (pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to))
    )

    bucket = pl.col("t").dt.truncate("1d").alias("bucket")
    qq = (
        q.with_columns(bucket)
        .group_by("bucket")
        .agg(
            o=pl.col("o").first(),
            h=pl.col("h").max(),
            l=pl.col("l").min(),
            c=pl.col("c").last(),
            v=pl.col("v").sum(),
            n=pl.col("n").sum().fill_null(0),
        )
        .sort("bucket")
    )
    df = qq.collect()
    items = [
        {
            "t": _isoz(t),
            "o": float(o),
            "h": float(h),
            "l": float(lo),
            "c": float(c),
            "v": int(v),
            "n": int(n),
        }
        for t, o, h, lo, c, v, n in zip(
            df["bucket"], df["o"], df["h"], df["l"], df["c"], df["v"], df["n"], strict=False
        )
    ]
    return JSONResponse(content={"symbol": symbol, "bars": items})


@router.get("/bars/minute")
async def get_minute(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    rth_only: bool = True,
):
    """Return minute OHLCV from warehouse parquet within a date range.

    When rth_only is true, only regular trading hours rows are returned.
    """
    # New warehouse paths:
    # data/warehouse/bars/mid_1min/venue=XNAS/symbol={symbol}/date=YYYY-MM-DD/bars.parquet
    try:
        ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
        ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="Invalid from/to format; expected YYYY-MM-DD"
        ) from e

    def _paths(symbol: str, ts_from: datetime, ts_to: datetime) -> list[str]:
        base = _base_dir() / "warehouse" / "bars" / "mid_1min" / "venue=XNAS" / f"symbol={symbol}"
        if not base.exists():
            return []
        dates = []
        d = ts_from.date()
        while d <= ts_to.date():
            dates.append(str(d))
            d = (datetime.combine(d, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)).date()
        out: list[str] = []
        for ds in dates:
            p = base / f"date={ds}" / "bars.parquet"
            if p.exists():
                out.append(str(p))
        return out

    paths = _paths(symbol, ts_from, ts_to)
    if not paths:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No 1-minute warehouse data available for {symbol} in date range "
                f"{from_date} to {to_date}. "
                "Run warehouse backfill first."
            ),
        )

    q = pl.scan_parquet(paths).filter(
        (pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to))
    )
    if rth_only:
        q = q.filter(pl.col("rth"))
    q = q.select(["t", "o", "h", "l", "c", "v"])  # minimal set for minute candles
    df = q.collect()
    items = [
        {"t": _isoz(t), "o": float(o), "h": float(h), "l": float(lo), "c": float(c), "v": int(v)}
        for t, o, h, lo, c, v in zip(
            df["t"], df["o"], df["h"], df["l"], df["c"], df["v"], strict=False
        )
    ]
    return JSONResponse(content={"symbol": symbol, "bars": items})


@router.get("/bars/minute_decimated")
async def get_minute_decimated(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    target: int = 10000,
    rth_only: bool = True,
):
    """Return minute OHLCV down-sampled to approximately `target` points.

    Uses stride-based bucketing without reading the full dataset into memory.
    """
    # New warehouse paths for minute bars
    try:
        ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
        ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="Invalid from/to format; expected YYYY-MM-DD"
        ) from e

    def _paths(symbol: str, ts_from: datetime, ts_to: datetime) -> list[str]:
        base = _base_dir() / "warehouse" / "bars" / "mid_1min" / "venue=XNAS" / f"symbol={symbol}"
        if not base.exists():
            return []
        dates = []
        d = ts_from.date()
        while d <= ts_to.date():
            dates.append(str(d))
            d = (datetime.combine(d, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)).date()
        out: list[str] = []
        for ds in dates:
            p = base / f"date={ds}" / "bars.parquet"
            if p.exists():
                out.append(str(p))
        return out

    paths = _paths(symbol, ts_from, ts_to)
    if not paths:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No 1-minute warehouse data available for {symbol} in date range {from_date} "
                f"to {to_date}. Run warehouse backfill first."
            ),
        )

    # Build base query with filters
    q = pl.scan_parquet(paths).filter(
        (pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to))
    )
    if rth_only:
        q = q.filter(pl.col("rth"))

    # Estimate stride using simple day-minute math; fall back to 1
    # We avoid reading the full dataset by estimating minutes from date span
    try:
        dt_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
        dt_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
        total_minutes = max(1, int((dt_to - dt_from).total_seconds() // 60))
    except Exception:
        total_minutes = 60 * 24 * 30
    stride = max(1, total_minutes // max(1, int(target)))
    # Round stride to sensible buckets (1m,5m,15m,30m,60m,120m)
    candidates = [1, 2, 5, 10, 15, 30, 60, 120, 240]
    stride = min(candidates, key=lambda c: abs(c - stride))

    bucket = (pl.col("t").dt.truncate(f"{stride}m")).alias("bucket")
    qq = (
        q.with_columns(bucket)
        .group_by("bucket")
        .agg(
            o=pl.col("o").first(),
            h=pl.col("h").max(),
            l=pl.col("l").min(),
            c=pl.col("c").last(),
            v=pl.col("v").sum(),
        )
        .sort("bucket")
    )
    df = qq.collect()
    items = [
        {"t": _isoz(t), "o": float(o), "h": float(h), "l": float(lo), "c": float(c), "v": int(v)}
        for t, o, h, lo, c, v in zip(
            df["bucket"], df["o"], df["h"], df["l"], df["c"], df["v"], strict=False
        )
    ]
    meta = {"stride_minutes": stride, "points": len(items)}
    return JSONResponse(content={"symbol": symbol, "bars": items, "meta": meta})


@router.get("/bars/hour")
async def get_hour(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    rth_only: bool = True,
):
    """Return 1-hour OHLCV aggregated from 1-minute parquet aligned to RTH.

    Buckets start 13:30Z with +1h steps (13:30→14:30, ... 19:30→20:00).
    Bucket time (t) is the bucket START in UTC.
    """
    # Use pre-aggregated 1h parquet from warehouse if available
    try:
        ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
        ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="Invalid from/to format; expected YYYY-MM-DD"
        ) from e

    base = _base_dir() / "warehouse" / "bars" / "mid_1h" / "venue=XNAS" / f"symbol={symbol}"
    paths: list[str] = []
    if base.exists():
        d = ts_from.date()
        while d <= ts_to.date():
            p = base / f"date={d}" / "bars.parquet"
            if p.exists():
                paths.append(str(p))
            d = (datetime.combine(d, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)).date()
    if not paths:
        _from = from_date
        _to = to_date
        raise HTTPException(
            status_code=404,
            detail=(
                f"No 1-hour warehouse data available for {symbol} in date range {_from} "
                f"to {_to}. Run warehouse backfill first."
            ),
        )

    qh = pl.scan_parquet(paths).filter(
        (pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to))
    )
    qh = qh.select(["t", "o", "h", "l", "c", "v"])  # minimal set for chart

    dfh = qh.collect()

    if dfh.height == 0:
        raise HTTPException(status_code=404, detail="No data rows in requested window")
    items = [
        {"t": _isoz(t), "o": float(o), "h": float(h), "l": float(lo), "c": float(c), "v": int(v)}
        for t, o, h, lo, c, v in zip(
            dfh["t"], dfh["o"], dfh["h"], dfh["l"], dfh["c"], dfh["v"], strict=False
        )
    ]

    return JSONResponse(content={"symbol": symbol, "bars": items})
