from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from backend.jobs.ingest import ingest_databento
from backend.jobs.derive import derive_bars
from backend.adapters.sqlite_catalog import SqliteCatalog


def _base_data_dir() -> Path:
    return Path(os.environ.get("HEWSTON_DATA_DIR", "data"))


def ensure_dataset(symbol: str, year: int, *, force: bool = False) -> str:
    """Ensure dataset exists by running ingest→derive→upsert; return dataset_id.
    This is a thin adapter; later we can formalize a MarketData implementation.
    """
    # Run pipeline (idempotent)
    ingest_databento(symbol=symbol, year=year, force=force)
    manifest = derive_bars(symbol=symbol, year=year, force=force)

    dataset_id = f"{symbol}-{year}-1m"
    base = _base_data_dir()

    # Build JSON arrays of file paths (repo-relative)
    raw_dir = base / "raw" / "databento" / symbol / str(year)
    derived_dir = base / "derived" / "bars" / symbol / str(year)
    raw_files = [str(raw_dir / "TRADES.dbn.zst"), str(raw_dir / "TBBO.dbn.zst")]
    bars_files = [str(derived_dir / "bars_1m.parquet"), str(derived_dir / "tbbo_1m.parquet")]

    # Compute total size bytes
    size_bytes = 0
    for p in raw_files + bars_files:
        try:
            size_bytes += Path(p).stat().st_size
        except FileNotFoundError:
            pass

    # Upsert via catalog adapter
    cat = SqliteCatalog()
    cat.upsert_dataset(
        {
            "dataset_id": dataset_id,
            "symbol": symbol,
            "from_date": f"{year}-01-01",
            "to_date": f"{year}-12-31",
            "products": ["TRADES", "TBBO"],
            "calendar_version": manifest.get("calendar_version", "v1"),
            "tz": manifest.get("tz", "America/New_York"),
            "raw_dbn": raw_files,
            "bars_parquet": bars_files,
            "bars_manifest_path": str(derived_dir / "bars_manifest.json"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": size_bytes,
            "status": "READY",
        }
    )

    return dataset_id

