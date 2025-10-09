"""Nautilus timestamp conversion tests (UTC ISO rendering)."""

import pandas as pd


def _to_utc_iso(ts):
    t = pd.Timestamp(ts)
    return (
        t.tz_localize("UTC") if t.tzinfo is None or t.tz is None else t.tz_convert("UTC")
    ).isoformat()


def test_pd_timestamp_utc_conversion_naive_and_aware():
    """Both naive and tz-aware timestamps are rendered with UTC suffix."""
    naive = pd.Timestamp("2024-10-01 09:30:00")  # tz-naive
    aware = pd.Timestamp("2024-10-01 09:30:00", tz="America/New_York")

    s_naive = _to_utc_iso(naive)
    s_aware = _to_utc_iso(aware)

    assert isinstance(s_naive, str)
    assert s_naive.endswith("Z") or s_naive.endswith("+00:00")
    assert isinstance(s_aware, str)
    assert s_aware.endswith("Z") or s_aware.endswith("+00:00")
