"""Data ingestion helpers (stubbed Databento writes for tests and local dev)."""

from __future__ import annotations

import os
import time
from pathlib import Path

DEFAULT_PRODUCTS = ("TRADES", "TBBO")


def _base_data_dir() -> Path:
    # Allow tests to override base data directory
    root = os.environ.get("HEWSTON_DATA_DIR", "data")
    return Path(root)


def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def ingest_databento(
    symbol: str, year: int, *, products: list[str] | None = None, force: bool = False
) -> dict[str, int]:
    """Simulate Databento ingestion by writing non-empty files.

    Respects HEWSTON_DATA_DIR (default: data); requires DATABENTO_API_KEY;
    idempotent unless force is True.

    Returns:
      dict[str, int]: Mapping product -> size_bytes.
    """
    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        raise SystemExit("DATABENTO_API_KEY not set")

    prods = list(products or DEFAULT_PRODUCTS)
    base = _base_data_dir() / "raw" / "databento" / symbol / str(year)

    sizes: dict[str, int] = {}
    for prod in prods:
        filename = f"{prod}.dbn.zst"
        out = base / filename
        _ensure_parent(out)

        start = time.perf_counter()
        if out.exists() and out.stat().st_size > 0 and not force:
            size = out.stat().st_size
            print(f"[ingest] {symbol} {year} {prod}: exists ({size} bytes) — skipping")
            sizes[prod] = size
            continue

        # Simulate content (1 KiB) — later stories will replace with real Databento SDK call
        data = (f"stub-dbento {symbol} {year} {prod}\n").encode() * 32
        _atomic_write(out, data)
        elapsed = time.perf_counter() - start
        size = out.stat().st_size
        print(f"[ingest] {symbol} {year} {prod}: wrote {size} bytes in {elapsed:.3f}s -> {out}")
        sizes[prod] = size

    return sizes
