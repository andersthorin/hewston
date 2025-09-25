#!/usr/bin/env python3
"""
Aggregate daily OHLCV from existing 1-minute bars per symbol/year.

Environment variables (similar to scripts/derive_bars_runner.py):
  HEWSTON_DATA_DIR   Base data dir (default: data)
  SYMBOLS            Comma-separated list or "ALL" (default: ALL)
  FROM               Optional ISO date (YYYY-MM-DD)
  TO                 Optional ISO date (YYYY-MM-DD)
  FORCE              If set (non-empty), overwrite outputs
  FORMAT             Output format (parquet only supported here)
  RTH_ONLY           Default true; filter to 09:30–16:00 America/New_York
  FILL_GAPS          Default false; if minutes exist with provider="carry_forward", drop them

Outputs:
  data/derived/bars/{SYMBOL}/{YEAR}/bars_1Day.parquet
  Catalog upsert: dataset_id = {SYMBOL}-{YEAR}-1d
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, timezone

import polars as pl

# Ensure repo root in path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.adapters.sqlite_catalog import SqliteCatalog  # type: ignore


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def discover_symbols(base: Path) -> List[str]:
    for sub in ("trades", "tbbo"):
        p = base / "raw" / "databento" / sub / "symbology.json"
        if p.exists():
            try:
                d = json.loads(p.read_text())
                syms = list(d.get("result", {}).keys())
                if syms:
                    return syms
            except Exception:
                pass
    # Fallback: discover from existing derived 1Min folders
    derived = base / "derived" / "bars"
    if derived.exists():
        out = sorted({p.name for p in derived.iterdir() if p.is_dir()})
        if out:
            return out
    return []


def discover_years_for_symbol(base: Path, symbol: str, from_date: Optional[str], to_date: Optional[str]) -> List[int]:
    years = []
    sym_dir = base / "derived" / "bars" / symbol
    if sym_dir.exists():
        for ydir in sym_dir.iterdir():
            if not ydir.is_dir():
                continue
            try:
                y = int(ydir.name)
            except ValueError:
                continue
            minute_path = ydir / "bars_1Min.parquet"
            if minute_path.exists():
                years.append(y)
    years.sort()
    if from_date and to_date:
        y1, y2 = int(from_date[:4]), int(to_date[:4])
        years = [y for y in years if y1 <= y <= y2]
    return years


def _load_minute(symbol: str, year: int, base: Path) -> Optional[pl.DataFrame]:
    path = base / "derived" / "bars" / symbol / str(year) / "bars_1Min.parquet"
    if not path.exists():
        return None
    try:
        return pl.read_parquet(path)
    except Exception as e:
        print(f"[daily-fast] {symbol} {year} read error: {e}")
        return None


def _filter_range(df: pl.DataFrame, from_date: Optional[str], to_date: Optional[str]) -> pl.DataFrame:
    if not from_date and not to_date:
        return df
    # t is timezone-aware UTC; filter inclusive
    expr = None
    if from_date:
        expr = (pl.col("t") >= pl.lit(from_date + "T00:00:00Z").str.strptime(pl.Datetime, strict=False, utc=True))
    if to_date:
        e2 = (pl.col("t") <= pl.lit(to_date + "T23:59:59Z").str.strptime(pl.Datetime, strict=False, utc=True))
        expr = e2 if expr is None else (expr & e2)
    return df.filter(expr) if expr is not None else df


def _aggregate_daily_from_minute(df: pl.DataFrame, *, rth_only: bool, drop_carry: bool) -> pl.DataFrame:
    sel = df
    if rth_only and "rth" in sel.columns:
        sel = sel.filter(pl.col("rth") == True)
    if drop_carry and "provider" in sel.columns:
        sel = sel.filter(pl.col("provider") != pl.lit("carry_forward"))
    if sel.is_empty():
        return pl.DataFrame({
            "t": pl.Series([], dtype=pl.Datetime(time_unit="us", time_zone="UTC")),
            "o": [], "h": [], "l": [], "c": [], "v": [], "n": [], "vw_num": [], "vw_mean": [],
        })
    # NY date key
    sel = sel.with_columns(
        pl.col("t").dt.convert_time_zone("America/New_York").dt.date().alias("ny_date")
    )
    # Aggregate
    grouped = (
        sel.group_by("ny_date")
        .agg(
            t_min=pl.col("t").min(),
            o=pl.col("o").first(),
            h=pl.col("h").max(),
            l=pl.col("l").min(),
            c=pl.col("c").last(),
            v=pl.col("v").sum(),
            n=pl.col("n").sum(),
            vw_num=(pl.col("vw") * pl.col("v")).sum(),
            vw_mean=pl.col("vw").mean(),
            corr=pl.when(pl.col("corr").is_not_null()).then(pl.col("corr")).otherwise(False).any(),
            provider=
                pl.when((pl.col("provider") == "trades").any())
                  .then(pl.lit("trades"))
                  .otherwise(
                      pl.when((pl.col("provider") == "tbbo").any())
                        .then(pl.lit("tbbo"))
                        .otherwise(pl.lit("unknown"))
                  ),
        )
    )
    # Compute timestamp bucket (UTC midnight of the NY date's UTC day is acceptable and matches 1D floor on UTC)
    daily = grouped.with_columns(
        # Use UTC floor of the min timestamp to align with existing 1D bucket behavior
        t=pl.col("t_min").dt.truncate("1d").dt.replace_time_zone("UTC"),
        vw=pl.when(pl.col("v") > 0).then(pl.col("vw_num") / pl.col("v")).otherwise(pl.col("vw_mean")),
        session=pl.lit("regular"),
        rth=pl.lit(True),
        adj=pl.lit("unadjusted"),
        tf=pl.lit("1Day"),
    ).drop(["t_min", "vw_num", "vw_mean", "ny_date"])
    return daily.sort("t")


def _write_daily(symbol: str, year: int, daily: pl.DataFrame, base: Path, force: bool) -> Tuple[Path, dict]:
    # Add symbol & bar_id columns before writing
    daily = (
        daily
        .with_columns(
            pl.lit(symbol).alias("symbol"),
            pl.concat_str([pl.lit(f"{symbol}-"), pl.col("t").dt.strftime("%Y-%m-%dT%H:%M:%SZ"), pl.lit("-1Day")]).alias("bar_id"),
        )
    )
    # Order columns to match derive.py
    cols = ["symbol","t","o","h","l","c","v","n","vw","tf","session","rth","adj","provider","corr","bar_id"]
    daily = daily.select(cols)

    out_dir = base / "derived" / "bars" / symbol / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bars_1Day.parquet"
    if out_path.exists() and not force:
        # read existing manifest if present and return
        man_path = out_dir / "bars_manifest.json"
        manifest = {}
        try:
            if man_path.exists():
                manifest = json.loads(man_path.read_text())
        except Exception:
            pass
        daily.write_parquet(out_path)  # still rewrite file for idempotency
        return out_path, manifest
    daily.write_parquet(out_path)
    # Manifest basic (leave derive_bars to compute richer fields normally)
    from_dt = daily["t"].min()
    to_dt = daily["t"].max()
    from_s = str(from_dt)[:10] if from_dt is not None else None
    to_s = str(to_dt)[:10] if to_dt is not None else None
    manifest = {
        "dataset_id": f"{symbol}-{year}-1d",
        "symbol": symbol,
        "interval": "1d",
        "from_date": from_s,
        "to_date": to_s,
        "products": ["TRADES", "TBBO"],
        "calendar_version": "v1",
        "tz": "America/New_York",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "bars_manifest.json").write_text(json.dumps(manifest, indent=2))
    return out_path, manifest


def main() -> int:
    base = Path(os.environ.get("HEWSTON_DATA_DIR", "data")).resolve()
    symbols_env = os.environ.get("SYMBOLS", "ALL").strip()
    from_date = os.environ.get("FROM") or None
    to_date = os.environ.get("TO") or None
    force = bool(os.environ.get("FORCE"))
    out_format = (os.environ.get("FORMAT", "parquet") or "parquet").lower()
    if out_format != "parquet":
        print(f"[daily-fast] Only parquet supported for now (got {out_format})")
        return 2
    rth_only = _bool_env("RTH_ONLY", True)
    fill_gaps = _bool_env("FILL_GAPS", False)

    if symbols_env.upper() == "ALL" or not symbols_env:
        symbols = discover_symbols(base)
    else:
        symbols = [s.strip() for s in symbols_env.replace(",", " ").split() if s.strip()]

    if not symbols:
        print("[daily-fast] No symbols discovered; check symbology.json or derived dirs")
        return 2

    cat = SqliteCatalog()

    for sym in symbols:
        years = discover_years_for_symbol(base, sym, from_date, to_date)
        if not years:
            print(f"[daily-fast] {sym}: no years with bars_1Min.parquet in range")
            continue
        for y in years:
            print(f"[daily-fast] {sym} {y} FROM={from_date} TO={to_date} rth_only={rth_only} drop_carry={not fill_gaps}")
            df = _load_minute(sym, y, base)
            if df is None or df.is_empty():
                print(f"[daily-fast] {sym} {y}: missing or empty 1Min parquet; skip")
                continue
            df = _filter_range(df, from_date, to_date)
            if df.is_empty():
                print(f"[daily-fast] {sym} {y}: no minutes in range; skip")
                continue
            daily = _aggregate_daily_from_minute(df, rth_only=rth_only, drop_carry=(not fill_gaps))
            if daily.is_empty():
                print(f"[daily-fast] {sym} {y}: aggregation yielded 0 rows; skip")
                continue
            out_path, manifest = _write_daily(sym, y, daily, base, force)
            # Upsert dataset in catalog
            dsid = f"{sym}-{y}-1d"
            try:
                size_bytes = out_path.stat().st_size
            except Exception:
                size_bytes = 0
            cat.upsert_dataset({
                "dataset_id": dsid,
                "symbol": sym,
                "from_date": manifest.get("from_date"),
                "to_date": manifest.get("to_date"),
                "products": ["TRADES", "TBBO"],
                "calendar_version": manifest.get("calendar_version", "v1"),
                "tz": manifest.get("tz", "America/New_York"),
                "raw_dbn": [],
                "bars_parquet": [str(out_path)],
                "bars_manifest_path": str((base / "derived" / "bars" / sym / str(y) / "bars_manifest.json")),
                "generated_at": manifest.get("created_at", datetime.now(timezone.utc).isoformat()),
                "size_bytes": size_bytes,
                "status": "READY",
            })
            print(f"[catalog] dataset_id={dsid} file={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

