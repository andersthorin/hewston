"""
Path utilities for consistent file and directory handling.

This module centralizes path construction logic to avoid duplication
across the backend codebase.
"""

import os
from pathlib import Path
from typing import Optional

from backend.constants import DEFAULT_DATA_DIR, DEFAULT_CATALOG_PATH


def get_base_data_dir() -> Path:
    """Get the base data directory from environment or default."""
    return Path(os.environ.get("HEWSTON_DATA_DIR", DEFAULT_DATA_DIR))


def get_catalog_path() -> Path:
    """Get the catalog database path from environment or default."""
    return Path(os.environ.get("HEWSTON_CATALOG_PATH", DEFAULT_CATALOG_PATH))


def get_raw_databento_dir(symbol: Optional[str] = None, year: Optional[int] = None) -> Path:
    """Get the raw Databento data directory, optionally for a specific symbol/year."""
    base = get_base_data_dir() / "raw" / "databento"
    if symbol and year:
        return base / symbol / str(year)
    elif symbol:
        return base / symbol
    return base


def get_derived_bars_dir(symbol: Optional[str] = None, year: Optional[int] = None) -> Path:
    """Get the derived bars directory, optionally for a specific symbol/year."""
    base = get_base_data_dir() / "derived" / "bars"
    if symbol and year:
        return base / symbol / str(year)
    elif symbol:
        return base / symbol
    return base


def get_backtests_dir(run_id: Optional[str] = None) -> Path:
    """Get the backtests directory, optionally for a specific run."""
    base = get_base_data_dir() / "backtests"
    if run_id:
        return base / run_id
    return base


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path
