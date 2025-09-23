from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import polars as pl


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


def derive_bars(symbol: str, year: int, *, force: bool = False) -> Dict[str, object]:
    base = _base_data_dir()
    raw_dir = base / "raw" / "databento" / symbol / str(year)
    trades_path = raw_dir / "TRADES.dbn.zst"
    tbbo_path = raw_dir / "TBBO.dbn.zst"

    if not trades_path.exists() or not tbbo_path.exists():
        raise SystemExit("raw DBN files missing; run ingest first")

    derived_dir = base / "derived" / "bars" / symbol / str(year)
    bars_path = derived_dir / "bars_1m.parquet"
    tbbo_out_path = derived_dir / "tbbo_1m.parquet"
    manifest_path = derived_dir / "bars_manifest.json"

    # Deterministic content; if not force and files exist, keep as-is
    if force or not bars_path.exists():
        _write_parquet(_make_bars_stub(symbol, year), bars_path)
    if force or not tbbo_out_path.exists():
        _write_parquet(_make_tbbo_stub(symbol, year), tbbo_out_path)

    input_hashes = {
        "TRADES.dbn.zst": _sha256(trades_path),
        "TBBO.dbn.zst": _sha256(tbbo_path),
    }
    output_hashes = {
        "bars_1m.parquet": _sha256(bars_path),
        "tbbo_1m.parquet": _sha256(tbbo_out_path),
    }

    from_date = f"{year}-01-01"
    to_date = f"{year}-12-31"

    manifest = {
        "dataset_id": f"{symbol}-{year}",
        "symbol": symbol,
        "interval": "1m",
        "from_date": from_date,
        "to_date": to_date,
        "rebar_params": {"interval": "1m"},
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "calendar_version": "NAZDAQ-v1",  # placeholder per spec
        "tz": "America/New_York",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Preserve existing manifest if present and not forcing, for deterministic re-runs
    if manifest_path.exists() and not force:
        try:
            with open(manifest_path, "r") as f:
                old = json.load(f)
            # Return the old one if hashes match
            if old.get("input_hashes") == input_hashes and old.get("output_hashes") == output_hashes:
                return old
        except Exception:
            pass

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest

