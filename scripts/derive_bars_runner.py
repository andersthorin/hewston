#!/usr/bin/env python3
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Iterable

# Ensure repo root in path
# Silence noisy SSL warning from urllib3 on macOS Python 3.9
import warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.jobs.derive import derive_bars  # type: ignore
from backend.adapters.sqlite_catalog import SqliteCatalog  # type: ignore


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
    return []


from typing import Optional

def discover_years(base: Path, from_date: Optional[str], to_date: Optional[str]) -> List[int]:
    trades = base / "raw" / "databento" / "trades"
    years = set()
    if trades.exists():
        for p in trades.glob("*.trades.dbn.zst"):
            m = re.search(r"-(\d{8})\.trades\.dbn", p.name)
            if m:
                years.add(int(m.group(1)[:4]))
    ys = sorted(years)
    if from_date and to_date:
        y1, y2 = int(from_date[:4]), int(to_date[:4])
        ys = [y for y in ys if y1 <= y <= y2]
    return ys


def main() -> int:
    base = Path(os.environ.get("HEWSTON_DATA_DIR", "data")).resolve()
    symbols_env = os.environ.get("SYMBOLS", "ALL").strip()
    from_date = os.environ.get("FROM") or None
    to_date = os.environ.get("TO") or None
    force = bool(os.environ.get("FORCE"))
    tf = os.environ.get("TF", "1Min")
    out_format = os.environ.get("FORMAT", "parquet").lower()
    # Defaults: for 1Day builds, prefer RTH_ONLY=True and FILL_GAPS=False unless explicitly overridden
    _fg_env = os.environ.get("FILL_GAPS")
    _rth_env = os.environ.get("RTH_ONLY")
    fill_gaps = (_fg_env if _fg_env is not None else "false").lower() in ("1","true","yes","on")
    rth_only_default = "true" if tf == "1Day" and _rth_env is None else "false"
    rth_only = (_rth_env if _rth_env is not None else rth_only_default).lower() in ("1","true","yes","on")

    if symbols_env.upper() == "ALL" or not symbols_env:
        symbols = discover_symbols(base)
    else:
        symbols = [s.strip() for s in symbols_env.replace(",", " ").split() if s.strip()]

    years = discover_years(base, from_date, to_date)

    if not symbols:
        print("[derive-bars] No symbols found; check symbology.json in data/raw/databento/{trades|tbbo}")
        return 2
    if not years:
        print("[derive-bars] No years found; check .dbn.zst files in data/raw/databento/trades")
        return 2

    cat = SqliteCatalog()
    for s in symbols:
        for y in years:
            print(f"[derive-bars] {s} {y} FROM={from_date} TO={to_date} tf={tf} fmt={out_format} force={force} fill_gaps={fill_gaps} rth_only={rth_only}")
            manifest = derive_bars(symbol=s, year=y, force=force, from_date=from_date, to_date=to_date, tf=tf, out_format=out_format, fill_gaps=fill_gaps, rth_only=rth_only)
            # Upsert dataset
            derived_dir = base / "derived" / "bars" / s / str(y)
            out_ext = out_format if out_format != "parquet" else "parquet"
            bars_file = str(derived_dir / f"bars_{tf}.{out_ext}")
            size_bytes = 0
            for p in [bars_file]:
                try:
                    size_bytes += Path(p).stat().st_size
                except FileNotFoundError:
                    pass
            tf_norm = tf.replace("Min","m").replace("Hour","h").replace("Day","d").lower()
            dsid = f"{s}-{y}-{tf_norm}"
            cat.upsert_dataset({
                "dataset_id": dsid,
                "symbol": s,
                "from_date": manifest.get("from_date"),
                "to_date": manifest.get("to_date"),
                "products": ["TRADES", "TBBO"],
                "calendar_version": manifest.get("calendar_version", "v1"),
                "tz": manifest.get("tz", "America/New_York"),
                "raw_dbn": [],
                "bars_parquet": [bars_file],
                "bars_manifest_path": str(derived_dir / "bars_manifest.json"),
                "generated_at": manifest.get("created_at"),
                "size_bytes": size_bytes,
                "status": "READY",
            })
            print(f"[catalog] dataset_id={dsid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

