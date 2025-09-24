from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl

import pandas as pd
from typing import Optional, Callable
from glob import glob
from databento import DBNStore
import sys, time


def _parse_date_from_filename(name: str) -> Optional[str]:
    # Expect pattern like xnas-itch-YYYYMMDD.trades.dbn.zst or .tbbo.dbn.zst
    import re
    m = re.search(r"-(\d{8})\.(?:trades|tbbo)\.dbn", name)
    return m.group(1) if m else None


def _read_symbology_id(base: Path, symbol: str) -> Optional[int]:
    # Prefer trades symbology.json
    for sub in ["trades", "tbbo"]:
        p = base / "raw" / "databento" / sub / "symbology.json"
        if p.exists():
            try:
                j = json.loads(p.read_text())
                rid = j.get("result", {}).get(symbol)
                if isinstance(rid, list) and len(rid) > 0:
                    s = rid[0].get("s")
                    return int(s) if s is not None else None
            except Exception:
                continue
    return None


def _derive_trades_minutes(files: list[str], instrument_id: int, progress: Optional[Callable[[int], None]] = None) -> pd.DataFrame:
    parts = []
    total = len(files)
    t0 = time.perf_counter()
    for i, f in enumerate(files):
        start = time.perf_counter()
        sys.stdout.write(f"[derive][trades] {i+1}/{total} {Path(f).name} …\n"); sys.stdout.flush()
        try:
            store = DBNStore.from_file(f)
            df = store.to_df()
        except Exception as e:
            sys.stdout.write(f"[derive][trades] {i+1}/{total} {Path(f).name} ERROR: {e}\n"); sys.stdout.flush()
            continue
        if "instrument_id" in df.columns:
            df = df[df["instrument_id"] == instrument_id]
        # Required columns: ts_event (ns), price, size
        if "ts_event" not in df.columns or "price" not in df.columns:
            sys.stdout.write(f"[derive][trades] {i+1}/{total} {Path(f).name} skipped (missing cols)\n"); sys.stdout.flush()
            continue
        ts = pd.to_datetime(df["ts_event"], unit="ns", utc=True)
        df = pd.DataFrame({
            "ts": ts,
            "price": pd.to_numeric(df["price"], errors="coerce"),
            "size": pd.to_numeric(df.get("size", 0), errors="coerce").fillna(0),
        })
        df = df.set_index("ts")
        o = df["price"].resample("1min").first()
        h = df["price"].resample("1min").max()
        l = df["price"].resample("1min").min()
        c = df["price"].resample("1min").last()
        v = df["size"].resample("1min").sum()
        n = df["price"].resample("1min").count()
        pvs = (df["price"] * df["size"]).resample("1min").sum()
        out = pd.concat([o, h, l, c, v, n, pvs], axis=1)
        out.columns = ["o", "h", "l", "c", "v", "n", "pvs"]
        out = out.dropna(subset=["o", "h", "l", "c"], how="any")
        parts.append(out.reset_index())
        # ETA
        elapsed = time.perf_counter() - t0
        avg = elapsed / (i+1)
        eta = avg * max(0, total - (i+1))
        sys.stdout.write(f"[derive][trades] {i+1}/{total} done in {time.perf_counter()-start:.2f}s, ETA {eta:.1f}s\n"); sys.stdout.flush()
        if progress:
            progress(i+1)
    if not parts:
        return pd.DataFrame(columns=["ts","o","h","l","c","v"])  # empty
    return pd.concat(parts, ignore_index=True)


def _derive_tbbo_minutes(files: list[str], instrument_id: int, progress: Optional[Callable[[int], None]] = None) -> pd.DataFrame:
    parts = []
    total = len(files)
    t0 = time.perf_counter()
    for i, f in enumerate(files):
        start = time.perf_counter()
        sys.stdout.write(f"[derive][tbbo]   {i+1}/{total} {Path(f).name} …\n"); sys.stdout.flush()
        try:
            store = DBNStore.from_file(f)
            df = store.to_df()
        except Exception as e:
            sys.stdout.write(f"[derive][tbbo]   {i+1}/{total} {Path(f).name} ERROR: {e}\n"); sys.stdout.flush()
            continue
        if "instrument_id" in df.columns:
            df = df[df["instrument_id"] == instrument_id]
        # Typical TBBO columns: bid_px, ask_px
        if "ts_event" not in df.columns or "bid_px" not in df.columns or "ask_px" not in df.columns:
            sys.stdout.write(f"[derive][tbbo]   {i+1}/{total} {Path(f).name} skipped (missing cols)\n"); sys.stdout.flush()
            continue
        ts = pd.to_datetime(df["ts_event"], unit="ns", utc=True)
        df = pd.DataFrame({
            "ts": ts,
            "bid_px": pd.to_numeric(df["bid_px"], errors="coerce"),
            "ask_px": pd.to_numeric(df["ask_px"], errors="coerce"),
        })
        df = df.set_index("ts")
        mid = (df["bid_px"] + df["ask_px"]) / 2.0
        mid_first = mid.resample("1min").first()
        mid_mean = mid.resample("1min").mean()
        out = pd.concat([mid_first, mid_mean], axis=1)
        out.columns = ["mid_first", "mid_mean"]
        out = out.dropna(how="any")
        parts.append(out.reset_index())
        elapsed = time.perf_counter() - t0
        avg = elapsed / (i+1)
        eta = avg * max(0, total - (i+1))
        sys.stdout.write(f"[derive][tbbo]   {i+1}/{total} done in {time.perf_counter()-start:.2f}s, ETA {eta:.1f}s\n"); sys.stdout.flush()
        if progress:
            progress(i+1)
    if not parts:
        return pd.DataFrame(columns=["ts","bid_mean","ask_mean","spread_mean"])  # empty
    return pd.concat(parts, ignore_index=True)


def _base_data_dir() -> Path:
    return Path(os.environ.get("HEWSTON_DATA_DIR", "data"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_parquet(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)


def _make_bars_stub(symbol: str, year: int) -> pl.DataFrame:
    # Deterministic tiny dataset (2 minutes) in UTC
    ts0 = f"{year}-01-01T00:00:00Z"
    ts1 = f"{year}-01-01T00:01:00Z"
    return pl.DataFrame(
        {
            "ts": [ts0, ts1],
            "o": [100.0, 101.0],
            "h": [101.0, 102.0],
            "l": [99.5, 100.5],
            "c": [100.5, 101.5],
            "v": [1000, 1200],
            "symbol": [symbol, symbol],
        }
    )


def _make_tbbo_stub(symbol: str, year: int) -> pl.DataFrame:
    ts0 = f"{year}-01-01T00:00:00Z"
    ts1 = f"{year}-01-01T00:01:00Z"
    return pl.DataFrame(
        {
            "ts": [ts0, ts1],
            "bid_mean": [100.0, 101.0],
            "ask_mean": [100.2, 101.2],
            "spread_mean": [0.2, 0.2],
            "symbol": [symbol, symbol],
        }
    )


def derive_bars(symbol: str, year: int, *, force: bool = False, from_date: Optional[str] = None, to_date: Optional[str] = None, tf: str = "1Min", out_format: str = "parquet", fill_gaps: bool = False, rth_only: bool = False) -> Dict[str, object]:
    base = _base_data_dir()
    # New layout: data/raw/databento/{trades|tbbo}/*.dbn.zst
    trades_dir = base / "raw" / "databento" / "trades"
    tbbo_dir = base / "raw" / "databento" / "tbbo"

    # If DBN directories are missing, fall back to stub
    if not trades_dir.exists() or not tbbo_dir.exists():
        # Backwards-compat: check old layout, else stub
        raw_dir_old = base / "raw" / "databento" / symbol / str(year)
        trades_path_old = raw_dir_old / "TRADES.dbn.zst"
        tbbo_path_old = raw_dir_old / "TBBO.dbn.zst"
        if not trades_path_old.exists() or not tbbo_path_old.exists():
            # Stub
            derived_dir = base / "derived" / "bars" / symbol / str(year)
            bars_path = derived_dir / "bars_1m.parquet"
            tbbo_out_path = derived_dir / "tbbo_1m.parquet"
            if force or not bars_path.exists():
                _write_parquet(_make_bars_stub(symbol, year), bars_path)
            if force or not tbbo_out_path.exists():
                _write_parquet(_make_tbbo_stub(symbol, year), tbbo_out_path)
            input_hashes = {}
            output_hashes = {
                "bars_1m.parquet": _sha256(bars_path),
                "tbbo_1m.parquet": _sha256(tbbo_out_path),
            }
            manifest_path = derived_dir / "bars_manifest.json"
            manifest = {
                "dataset_id": f"{symbol}-{year}-1m",
                "symbol": symbol,
                "interval": "1m",
                "from_date": f"{year}-01-01",
                "to_date": f"{year}-12-31",
                "rebar_params": {"interval": "1m"},
                "input_hashes": input_hashes,
                "output_hashes": output_hashes,
                "calendar_version": "NAZDAQ-v1",
                "tz": "America/New_York",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=2))
            return manifest
        # Otherwise act as if single-file layout
        trades_files = [str(trades_path_old)]
        tbbo_files = [str(tbbo_path_old)]
    else:
        trades_files = sorted(glob(str(trades_dir / "*.trades.dbn.zst")))
        tbbo_files = sorted(glob(str(tbbo_dir / "*.tbbo.dbn.zst")))
        # Restrict to selected window using filename date (YYYYMMDD)
        def _in_window(path: str) -> bool:
            ymd = _parse_date_from_filename(path)
            if not ymd:
                return False
            ok = True
            if year:
                ok = ok and (ymd[:4] == str(year))
            if from_date:
                ok = ok and (ymd >= str(from_date).replace('-', ''))
            if to_date:
                ok = ok and (ymd <= str(to_date).replace('-', ''))
            return ok
        trades_files = [f for f in trades_files if _in_window(f)]
        tbbo_files = [f for f in tbbo_files if _in_window(f)]

    if not trades_files:
        raise SystemExit(f"No trades DBN files found for year={year}")

    inst_id = _read_symbology_id(base, symbol)
    if inst_id is None:
        raise SystemExit(f"Symbology missing or no instrument id for symbol {symbol}")

    # --- Derive TRADES → minute OHLCV+N+VW ---
    total_steps = len(trades_files) + len(tbbo_files)
    t0_total = time.perf_counter()
    bar_len = 30
    def make_progress(offset: int):
        def _p(i: int) -> None:
            processed = offset + i
            if total_steps <= 0 or processed <= 0:
                return
            pct = int(processed * 100 / total_steps)
            elapsed = time.perf_counter() - t0_total
            eta = (elapsed / processed) * max(0, total_steps - processed)
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"[derive][total] [{bar}] {pct}% ETA {eta:.1f}s ({processed}/{total_steps})\n"); sys.stdout.flush()
        return _p
    trades_min = _derive_trades_minutes(trades_files, inst_id, progress=make_progress(0))
    if trades_min.empty:
        raise SystemExit("No trades found for given symbol/year")
    # Collapse duplicates across files and compute VW
    trades_min["ts"] = trades_min["ts"].dt.floor("min").dt.tz_convert("UTC")
    trades_min = trades_min.groupby("ts", as_index=False).agg({
        "o":"first","h":"max","l":"min","c":"last","v":"sum","n":"sum","pvs":"sum"
    })
    trades_min["vw"] = trades_min.apply(lambda r: (r["pvs"] / r["v"]) if r["v"] > 0 else pd.NA, axis=1)
    trades_min = trades_min.drop(columns=["pvs"])
    trades_min = trades_min.rename(columns={"ts":"t"})

    # --- Derive TBBO → minute mid fills ---
    tbbo_min = pd.DataFrame(columns=["t","mid_first","mid_mean"])  # default empty
    if tbbo_files:
        tbbo_min = _derive_tbbo_minutes(tbbo_files, inst_id, progress=make_progress(len(trades_files)))
        if not tbbo_min.empty:
            tbbo_min["ts"] = tbbo_min["ts"].dt.floor("min").dt.tz_convert("UTC")
            tbbo_min = tbbo_min.groupby("ts", as_index=False).agg({"mid_first":"first","mid_mean":"mean"})
            tbbo_min = tbbo_min.rename(columns={"ts":"t"})
        else:
            tbbo_min = pd.DataFrame(columns=["t","mid_first","mid_mean"])

    # --- Combine TRADES primary with TBBO gap fill ---
    combined = pd.merge(trades_min, tbbo_min, on="t", how="outer", sort=True)
    has_trades = combined["v"].fillna(0) > 0

    def _choose(col_trade: str, default=None):
        return combined[col_trade].where(has_trades, other=default)

    o = _choose("o")
    h = _choose("h")
    l = _choose("l")
    c = _choose("c")
    v = _choose("v", 0).fillna(0)
    n = _choose("n", 0).fillna(0)
    vw = combined["vw"].where(has_trades, other=combined.get("mid_mean"))

    # Where no trades, fill OHLC from TBBO mid_first
    o = o.where(has_trades, other=combined.get("mid_first"))
    h = h.where(has_trades, other=combined.get("mid_first"))
    l = l.where(has_trades, other=combined.get("mid_first"))
    c = c.where(has_trades, other=combined.get("mid_first"))

    provider = pd.Series(pd.NA, index=combined.index, dtype="object")
    provider = provider.where(~has_trades, other="databento_trades")
    provider = provider.where(has_trades | combined.get("mid_first").notna(), other="databento_tbbo_fill")

    bars_min = pd.DataFrame({
        "t": combined["t"],
        "o": o.astype(float),
        "h": h.astype(float),
        "l": l.astype(float),
        "c": c.astype(float),
        "v": v.astype("int64"),
        "n": n.astype("int64"),
        "vw": vw.astype(float),
        "provider": provider,
        "corr": False,
    }).dropna(subset=["t"]).sort_values("t")

    # Optional carry-forward gap fill
    if fill_gaps and not bars_min.empty:
        start_t = pd.to_datetime(from_date + "T00:00:00Z") if from_date else bars_min["t"].min()
        end_t = pd.to_datetime(to_date + "T23:59:00Z") if to_date else bars_min["t"].max()
        freq = "1min"
        full_idx = pd.date_range(start=start_t, end=end_t, freq=freq, tz="UTC")
        bars_min = bars_min.set_index("t").reindex(full_idx)
        # forward-fill close; synthesize carry-forward bars
        ffc = bars_min["c"].ffill()
        carry = bars_min[bars_min["o"].isna()].copy()
        carry["o"] = ffc
        carry["h"] = ffc
        carry["l"] = ffc
        carry["c"] = ffc
        carry["v"] = 0
        carry["n"] = 0
        carry["vw"] = ffc
        carry["provider"] = "carry_forward"
        carry["corr"] = False
        bars_min.update(carry)
        bars_min = bars_min.reset_index().rename(columns={"index":"t"})
    else:
        bars_min = bars_min.reset_index(drop=True)

    # Session / RTH labeling (America/New_York)
    def _label_session(df: pd.DataFrame) -> pd.DataFrame:
        local = df["t"].dt.tz_convert("America/New_York")
        mins = local.dt.hour * 60 + local.dt.minute
        pre = (mins >= 4*60) & (mins < 9*60 + 30)
        regular = (mins >= 9*60 + 30) & (mins < 16*60)
        post = (mins >= 16*60) & (mins < 20*60)
        session = pd.Series("off", index=df.index)
        session = session.mask(pre, "pre")
        session = session.mask(regular, "regular")
        session = session.mask(post, "post")
        df["session"] = session
        df["rth"] = regular
        return df

    bars_min = _label_session(bars_min)
    if rth_only:
        bars_min = bars_min[bars_min["rth"]]

    # Resample to target tf if needed
    tf_map = {"1Min":"1min","5Min":"5min","15Min":"15min","1Hour":"1H","1Day":"1D"}
    if tf not in tf_map:
        raise SystemExit(f"Unsupported tf={tf}")
    if tf != "1Min":
        freq = tf_map[tf]
        bars_min = bars_min.sort_values("t")
        bars_min["bucket"] = bars_min["t"].dt.floor(freq)
        def _agg(g: pd.DataFrame) -> pd.Series:
            vv = g["v"].sum()
            if vv > 0:
                vw_val = (g["vw"] * g["v"]).sum() / vv
            else:
                vw_val = g["vw"].mean(skipna=True)
            provider_val = "databento_trades" if (g["v"].sum() > 0) else "databento_tbbo_fill"
            return pd.Series({
                "t": g["bucket"].iloc[0],
                "o": g["o"].iloc[0],
                "h": g["h"].max(),
                "l": g["l"].min(),
                "c": g["c"].iloc[-1],
                "v": vv,
                "n": g["n"].sum(),
                "vw": vw_val,
                "provider": provider_val,
                "corr": g["corr"].any(),
                "session": g["session"].mode(dropna=True).iloc[0] if not g["session"].mode(dropna=True).empty else pd.NA,
                "rth": g["rth"].any(),
            })
        bars_min = bars_min.groupby("bucket", as_index=False).apply(_agg, include_groups=False)

    # Finalize schema
    bars = bars_min.copy()
    bars["symbol"] = symbol
    bars["tf"] = tf
    bars["adj"] = "unadjusted"
    bars["bar_id"] = bars.apply(lambda r: f"{symbol}-{r['t'].strftime('%Y-%m-%dT%H:%M:%SZ')}-{tf}", axis=1)
    # Order columns per spec
    cols = ["symbol","t","o","h","l","c","v","n","vw","tf","session","rth","adj","provider","corr","bar_id"]
    bars = bars[cols].sort_values("t")

    # Write outputs per year/tf
    derived_dir = base / "derived" / "bars" / symbol / str(year)
    derived_dir.mkdir(parents=True, exist_ok=True)
    tf_key = {"Min":"m","Hour":"h","Day":"d"}
    tf_norm = tf.replace("Min","m").replace("Hour","h").replace("Day","d").lower()
    out_path = derived_dir / f"bars_{tf}.parquet" if out_format == "parquet" else derived_dir / f"bars_{tf}.{out_format}"

    if out_format == "parquet":
        # Ensure timezone-aware timestamp in Polars
        pl.from_pandas(bars).write_parquet(str(out_path))
    elif out_format == "csv":
        bars_out = bars.copy(); bars_out["t"] = bars_out["t"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        bars_out.to_csv(out_path, index=False)
    elif out_format == "jsonl":
        bars_out = bars.copy(); bars_out["t"] = bars_out["t"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        bars_out.to_json(out_path, orient="records", lines=True)
    else:
        raise SystemExit(f"Unsupported out_format={out_format}")

    # Hashes & manifest
    input_hashes = {"trades_files": len(trades_files), "tbbo_files": len(tbbo_files)}
    output_hashes = {out_path.name: _sha256(out_path)}

    # Dates from bars
    try:
        from_date = bars["t"].min().strftime("%Y-%m-%d")
        to_date = bars["t"].max().strftime("%Y-%m-%d")
    except Exception:
        from_date = f"{year}-01-01"
        to_date = f"{year}-12-31"

    manifest = {
        "dataset_id": f"{symbol}-{year}-{tf_norm}",
        "symbol": symbol,
        "interval": tf_norm,
        "from_date": from_date,
        "to_date": to_date,
        "rebar_params": {"interval": tf},
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "calendar_version": "NAZDAQ-v1",
        "tz": "America/New_York",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    manifest_path = derived_dir / "bars_manifest.json"
    if manifest_path.exists() and not force:
        try:
            old = json.loads(manifest_path.read_text())
            return old
        except Exception:
            pass

    manifest_path.write_text(json.dumps(manifest, indent=2))
    # Print summary
    try:
        sz = out_path.stat().st_size
        print(f"[derive][summary] {symbol} {tf} rows={len(bars)} size_bytes={sz} file={out_path.name}")
    except Exception:
        pass
    return manifest

