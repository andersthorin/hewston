"""
Datetime utilities for consistent timestamp handling.

This module centralizes datetime formatting and parsing logic
to avoid duplication across the backend codebase.
"""

from datetime import datetime, timezone
from typing import Tuple, Union

import pandas as pd


def utc_now() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def normalize_timestamp(ts_val: Union[str, datetime, pd.Timestamp]) -> Tuple[int, str]:
    """
    Normalize a timestamp value to (epoch_seconds, iso_string).
    
    Returns:
        Tuple of (epoch_seconds_int, iso_string_z) for robust joining and client parsing.
    """
    try:
        dt = pd.to_datetime(ts_val, utc=True)
        # epoch seconds as int for join keys
        epoch = int(dt.timestamp())
        # ISO 8601 Z string for client
        iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return epoch, iso
    except Exception:
        # Fallback: try string manipulation
        s = str(ts_val)
        s2 = s.replace(" UTC", "Z").replace(" ", "T").replace("+00:00", "Z")
        try:
            dt = pd.to_datetime(s2, utc=True)
            return int(dt.timestamp()), dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            # Best effort: fallback to original string, epoch 0
            return 0, s


def format_iso_timestamp(dt: datetime) -> str:
    """Format datetime as ISO 8601 string with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(iso_string: str) -> datetime:
    """Parse ISO 8601 string to UTC datetime."""
    return pd.to_datetime(iso_string, utc=True).to_pydatetime()
