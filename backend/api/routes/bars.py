from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

import polars as pl
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()


def _base_dir() -> Path:
    return Path(os.getenv("HEWSTON_DATA_DIR", "data")).resolve()


def _years_in_range(symbol: str, from_date: Optional[str], to_date: Optional[str]) -> List[int]:
    base = _base_dir() / "derived" / "bars" / symbol
    ys: List[int] = []
    if base.exists():
        for p in base.iterdir():
            if p.is_dir():
                try:
                    ys.append(int(p.name))
                except Exception:
                    pass
    ys = sorted(ys)
    if from_date:
        y1 = int(from_date[:4])
        ys = [y for y in ys if y >= y1]
    if to_date:
        y2 = int(to_date[:4])
        ys = [y for y in ys if y <= y2]
    return ys


def _paths_for(symbol: str, years: List[int], tf: str) -> List[str]:
    base = _base_dir() / "derived" / "bars" / symbol
    fname = f"bars_{tf}.parquet"
    return [str(base / str(y) / fname) for y in years if (base / str(y) / fname).exists()]


def _isoz(ts: datetime | str | None) -> Optional[str]:
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    try:
        return datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        try:
            return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None


@router.get("/bars/daily")
async def get_daily(
    symbol: str,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    years = _years_in_range(symbol, from_date, to_date)
    if not years:
        raise HTTPException(status_code=404, detail="No data for symbol/year range")
    paths = _paths_for(symbol, years, tf="1Day")
    if not paths:
        raise HTTPException(status_code=404, detail="No daily parquet files found")

    # Filter range with predicate pushdown
    q = pl.scan_parquet(paths)
    if from_date:
        ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
        q = q.filter(pl.col("t") >= pl.lit(ts_from))
    if to_date:
        ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
        q = q.filter(pl.col("t") <= pl.lit(ts_to))
    q = q.select(["t", "o", "h", "l", "c", "v", "n"])  # minimal set for chart
    df = q.collect()
    items = [
        {
            "t": _isoz(t),
            "o": float(o),
            "h": float(h),
            "l": float(l),
            "c": float(c),
            "v": int(v),
            "n": int(n),
        }
        for t, o, h, l, c, v, n in zip(df["t"], df["o"], df["h"], df["l"], df["c"], df["v"], df["n"])
    ]
    return JSONResponse(content={"symbol": symbol, "bars": items})


@router.get("/bars/minute")
async def get_minute(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    rth_only: bool = True,
):
    years = _years_in_range(symbol, from_date, to_date)
    if not years:
        raise HTTPException(status_code=404, detail="No data for symbol/year range")
    paths = _paths_for(symbol, years, tf="1Min")
    if not paths:
        raise HTTPException(status_code=404, detail="No minute parquet files found")

    ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
    ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
    q = pl.scan_parquet(paths).filter((pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to)))
    if rth_only:
        q = q.filter(pl.col("rth") == True)
    q = q.select(["t", "o", "h", "l", "c", "v"])  # minimal set for minute candles
    df = q.collect()
    items = [
        {"t": _isoz(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": int(v)}
        for t, o, h, l, c, v in zip(df["t"], df["o"], df["h"], df["l"], df["c"], df["v"])
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
    years = _years_in_range(symbol, from_date, to_date)
    if not years:
        raise HTTPException(status_code=404, detail="No data for symbol/year range")
    paths = _paths_for(symbol, years, tf="1Min")
    if not paths:
        raise HTTPException(status_code=404, detail="No minute parquet files found")

    # Build base query with filters
    ts_from = datetime.fromisoformat(from_date + "T00:00:00+00:00")
    ts_to = datetime.fromisoformat(to_date + "T23:59:59+00:00")
    q = pl.scan_parquet(paths).filter((pl.col("t") >= pl.lit(ts_from)) & (pl.col("t") <= pl.lit(ts_to)))
    if rth_only:
        q = q.filter(pl.col("rth") == True)

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
        {"t": _isoz(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": int(v)}
        for t, o, h, l, c, v in zip(df["bucket"], df["o"], df["h"], df["l"], df["c"], df["v"])
    ]
    meta = {"stride_minutes": stride, "points": len(items)}
    return JSONResponse(content={"symbol": symbol, "bars": items, "meta": meta})

