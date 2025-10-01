"""
Datetime utilities for consistent timestamp handling.

This module centralizes datetime formatting and parsing logic
to avoid duplication across the backend codebase.
"""

from datetime import datetime, timezone
from typing import Tuple, Union, Optional

import pandas as pd


def utc_now() -> datetime:
    """Get current UTC timestamp as a timezone-aware datetime object."""
    return datetime.now(timezone.utc)


def _to_datetime_utc(val: Union[str, int, float, datetime, pd.Timestamp]) -> datetime:
    """Convert supported inputs to a timezone-aware UTC datetime."""
    if isinstance(val, datetime):
        # If naive, assume UTC
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, pd.Timestamp):
        return val.tz_convert("UTC").to_pydatetime() if val.tzinfo else val.tz_localize("UTC").to_pydatetime()
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(float(val), tz=timezone.utc)
    if isinstance(val, str):
        # Preserve exact 'Z' formatting when input uses it by returning the string later
        return pd.to_datetime(val, utc=True).to_pydatetime()
    raise TypeError("Unsupported timestamp type")


def normalize_timestamp(ts_val: Union[str, int, float, datetime, pd.Timestamp]) -> Tuple[int, str]:
    """
    Normalize a timestamp value to (epoch_seconds, iso_string).
    - For datetime/Timestamp: iso_string == dt.isoformat()
    - For epoch int/float: iso_string == ISO with microseconds when present
    - For string '...Z': iso_string preserved as provided
    """
    if ts_val is None:
        raise TypeError("timestamp value is None")

    if isinstance(ts_val, str):
        # Accept only ISO-like strings
        try:
            dt = _to_datetime_utc(ts_val)
        except Exception as e:
            raise ValueError("invalid timestamp string") from e
        epoch = int(dt.timestamp())
        # Preserve 'Z' if user provided it exactly
        if ts_val.endswith("Z"):
            return epoch, ts_val
        return epoch, dt.isoformat()

    # datetime / pandas / epoch numbers
    dt = _to_datetime_utc(ts_val)
    epoch = int(dt.timestamp())
    return epoch, dt.isoformat()


def format_iso_timestamp(val: Union[datetime, pd.Timestamp, str, int, float]) -> str:
    """Format various inputs to ISO 8601 string.
    - datetime / pandas.Timestamp: dt.isoformat()
    - str: returned as-is
    - epoch (int/float): converted to UTC datetime then .isoformat()
    """
    if isinstance(val, str):
        return val
    dt = _to_datetime_utc(val)  # may raise for unsupported types
    return dt.isoformat()


def parse_iso_timestamp(iso_string: str) -> datetime:
    """Parse ISO 8601 string to UTC datetime."""
    return pd.to_datetime(iso_string, utc=True).to_pydatetime()
