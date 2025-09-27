"""
Tests for backend/utils/datetime.py utility functions.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from backend.utils.datetime import (
    utc_now,
    normalize_timestamp,
    format_iso_timestamp,
)


class TestDatetimeUtilities:
    """Test suite for datetime utility functions."""

    def test_utc_now_returns_utc_datetime(self):
        """Test utc_now returns a UTC datetime object."""
        result = utc_now()
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_utc_now_is_current_time(self):
        """Test utc_now returns approximately current time."""
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        
        # Should be within a reasonable time window (1 second)
        assert before <= result <= after
        assert (after - before).total_seconds() < 1.0

    def test_normalize_timestamp_with_datetime(self):
        """Test normalize_timestamp with datetime object."""
        dt = datetime(2023, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        epoch_seconds, iso_string = normalize_timestamp(dt)
        
        assert isinstance(epoch_seconds, int)
        assert isinstance(iso_string, str)
        assert epoch_seconds == int(dt.timestamp())
        assert iso_string == dt.isoformat()

    def test_normalize_timestamp_with_pandas_timestamp(self):
        """Test normalize_timestamp with pandas Timestamp."""
        ts = pd.Timestamp('2023-01-15 10:30:45', tz='UTC')
        
        epoch_seconds, iso_string = normalize_timestamp(ts)
        
        assert isinstance(epoch_seconds, int)
        assert isinstance(iso_string, str)
        assert epoch_seconds == int(ts.timestamp())
        # Pandas timestamp ISO format might differ slightly, so check components
        assert '2023-01-15T10:30:45' in iso_string

    def test_normalize_timestamp_with_string(self):
        """Test normalize_timestamp with ISO string."""
        iso_str = '2023-01-15T10:30:45Z'
        
        epoch_seconds, iso_string = normalize_timestamp(iso_str)
        
        assert isinstance(epoch_seconds, int)
        assert isinstance(iso_string, str)
        assert iso_string == iso_str
        # Check that epoch conversion is correct
        expected_dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        assert epoch_seconds == int(expected_dt.timestamp())

    def test_normalize_timestamp_with_epoch_int(self):
        """Test normalize_timestamp with epoch seconds as integer."""
        epoch = 1673776245  # 2023-01-15 10:30:45 UTC
        
        epoch_seconds, iso_string = normalize_timestamp(epoch)
        
        assert isinstance(epoch_seconds, int)
        assert isinstance(iso_string, str)
        assert epoch_seconds == epoch
        # Check ISO string is correct
        expected_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        assert iso_string == expected_dt.isoformat()

    def test_normalize_timestamp_with_epoch_float(self):
        """Test normalize_timestamp with epoch seconds as float."""
        epoch = 1673776245.123  # With microseconds
        
        epoch_seconds, iso_string = normalize_timestamp(epoch)
        
        assert isinstance(epoch_seconds, int)
        assert isinstance(iso_string, str)
        assert epoch_seconds == int(epoch)  # Should truncate to integer
        # Check ISO string includes microseconds
        expected_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        assert iso_string == expected_dt.isoformat()

    def test_normalize_timestamp_edge_cases(self):
        """Test normalize_timestamp with edge cases."""
        # Test with None (should handle gracefully or raise appropriate error)
        with pytest.raises((TypeError, ValueError)):
            normalize_timestamp(None)
        
        # Test with invalid string
        with pytest.raises((ValueError, TypeError)):
            normalize_timestamp("invalid-date-string")

    def test_format_iso_timestamp_with_datetime(self):
        """Test format_iso_timestamp with datetime object."""
        dt = datetime(2023, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        
        result = format_iso_timestamp(dt)
        
        assert isinstance(result, str)
        assert result == dt.isoformat()
        assert 'T' in result
        assert result.endswith('+00:00') or result.endswith('Z')

    def test_format_iso_timestamp_with_pandas_timestamp(self):
        """Test format_iso_timestamp with pandas Timestamp."""
        ts = pd.Timestamp('2023-01-15 10:30:45.123456', tz='UTC')
        
        result = format_iso_timestamp(ts)
        
        assert isinstance(result, str)
        assert '2023-01-15T10:30:45' in result
        assert 'T' in result

    def test_format_iso_timestamp_with_string(self):
        """Test format_iso_timestamp with string input."""
        iso_str = '2023-01-15T10:30:45Z'
        
        result = format_iso_timestamp(iso_str)
        
        assert isinstance(result, str)
        assert result == iso_str

    def test_format_iso_timestamp_with_epoch(self):
        """Test format_iso_timestamp with epoch timestamp."""
        epoch = 1673776245
        
        result = format_iso_timestamp(epoch)
        
        assert isinstance(result, str)
        expected_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        assert result == expected_dt.isoformat()

    def test_timestamp_consistency(self):
        """Test that normalize and format functions are consistent."""
        original_dt = datetime(2023, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        # Normalize then format should give same result as direct format
        epoch, iso_from_normalize = normalize_timestamp(original_dt)
        iso_from_format = format_iso_timestamp(original_dt)
        
        assert iso_from_normalize == iso_from_format
        
        # Round trip should preserve the timestamp
        epoch2, iso2 = normalize_timestamp(iso_from_normalize)
        assert epoch == epoch2
        assert iso_from_normalize == iso2

    def test_timezone_handling(self):
        """Test proper timezone handling in utilities."""
        # Test with naive datetime (should be treated as UTC)
        naive_dt = datetime(2023, 1, 15, 10, 30, 45)
        
        # The function should handle this appropriately
        # (either by assuming UTC or raising an error)
        try:
            epoch, iso = normalize_timestamp(naive_dt)
            # If it succeeds, check the result makes sense
            assert isinstance(epoch, int)
            assert isinstance(iso, str)
        except (ValueError, TypeError):
            # It's also acceptable to reject naive datetimes
            pass

    def test_microsecond_precision(self):
        """Test that microsecond precision is preserved where possible."""
        dt_with_microseconds = datetime(2023, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        
        epoch, iso = normalize_timestamp(dt_with_microseconds)
        formatted = format_iso_timestamp(dt_with_microseconds)
        
        # ISO strings should include microseconds
        assert '.123456' in iso or '123456' in iso
        assert '.123456' in formatted or '123456' in formatted
        
        # Epoch should be integer (microseconds lost in epoch conversion)
        assert isinstance(epoch, int)
