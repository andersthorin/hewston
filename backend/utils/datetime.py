"""Datetime utilities for consistent timestamp handling.

This module centralizes datetime formatting and parsing logic
to avoid duplication across the backend codebase.
"""

from datetime import UTC, datetime

import pandas as pd

# Thresholds and divisors for epoch unit detection
NS_THRESHOLD = 1_000_000_000_000_000  # nanoseconds threshold (>= 1e15)
MS_THRESHOLD = 1_000_000_000_000      # milliseconds threshold (>= 1e12)
SEC_TO_NS_DIVISOR = 1_000_000_000     # 1e9
MS_TO_SEC_DIVISOR = 1_000             # 1e3


def utc_now() -> datetime:
    """Get current UTC timestamp as a timezone-aware datetime object."""
    return datetime.now(UTC)


def _to_datetime_utc(val: str | int | float | datetime | pd.Timestamp) -> datetime:
    """Convert supported inputs to a timezone-aware UTC datetime.

    - Supports epoch provided in seconds, milliseconds, or nanoseconds.
    """
    if isinstance(val, datetime):
        # If naive, assume UTC
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    if isinstance(val, pd.Timestamp):
        return (
            val.tz_convert("UTC").to_pydatetime()
            if val.tzinfo
            else val.tz_localize("UTC").to_pydatetime()
        )
    if isinstance(val, int | float):
        # Detect unit by magnitude. Fallback avoids OverflowError on very large integers.
        try:
            if isinstance(val, int):
                a = abs(val)
                # Heuristics: ns >= 1e15, ms >= 1e12
                if a >= NS_THRESHOLD:  # nanoseconds
                    v = val / SEC_TO_NS_DIVISOR
                elif a >= MS_THRESHOLD:  # milliseconds
                    v = val / MS_TO_SEC_DIVISOR
                else:  # seconds
                    v = float(val)
            else:
                # For floats assume seconds
                v = float(val)
            return datetime.fromtimestamp(v, tz=UTC)
        except Exception:
            # Last resort: interpret as nanoseconds
            return datetime.fromtimestamp(float(val) / SEC_TO_NS_DIVISOR, tz=UTC)
    if isinstance(val, str):
        # Preserve exact 'Z' formatting when input uses it by returning the string later
        return pd.to_datetime(val, utc=True).to_pydatetime()
    raise TypeError("Unsupported timestamp type")


def normalize_timestamp(ts_val: str | int | float | datetime | pd.Timestamp) -> tuple[int, str]:
    """Normalize a timestamp value to (epoch_seconds, iso_string).

    - For datetime/Timestamp: iso_string == dt.isoformat()
    - For epoch int/float: iso_string == ISO with microseconds when present
    - For string '...Z': iso_string preserved as provided.
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


def format_iso_timestamp(val: datetime | pd.Timestamp | str | int | float) -> str:
    """Format various inputs to ISO 8601 string.

    - datetime / pandas.Timestamp: dt.isoformat()
    - str: returned as-is
    - epoch (int/float): converted to UTC datetime then .isoformat().
    """
    if isinstance(val, str):
        return val
    dt = _to_datetime_utc(val)  # may raise for unsupported types
    return dt.isoformat()


def parse_iso_timestamp(iso_string: str) -> datetime:
    """Parse ISO 8601 string to UTC datetime."""
    return pd.to_datetime(iso_string, utc=True).to_pydatetime()
