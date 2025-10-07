import math

import pytest

from backend.utils.metrics import compute_cumulative_metrics


def test_compute_cumulative_metrics_basic():
    equity = [
        {"ts_utc": "2024-01-01T00:00:00Z", "value": 100.0},
        {"ts_utc": "2024-01-01T00:01:00Z", "value": 101.0},
        {"ts_utc": "2024-01-01T00:02:00Z", "value": 100.5},
        {"ts_utc": "2024-01-01T00:03:00Z", "value": 102.0},
    ]
    realized = [
        ("2024-01-01T00:01:00Z", 5.0),
        ("2024-01-01T00:03:00Z", 3.0),
    ]

    series = compute_cumulative_metrics(equity, realized, bar_minutes=1)
    # Length matches equity
    assert len(series) == len(equity)

    # First point: no return, total_return 0, realized_pnl None
    ts0, m0 = series[0]
    assert ts0 == "2024-01-01T00:00:00+00:00" or ts0.endswith("Z")
    assert m0["equity"] == 100.0
    assert m0["return"] is None
    assert abs(m0["total_return"]) < 1e-12
    assert m0["realized_pnl"] is None

    # Second point: +1% return, realized_pnl 5.0, win_rate 1.0
    _, m1 = series[1]
    assert pytest.approx(m1["return"], rel=1e-9) == 0.01
    assert m1["realized_pnl"] == 5.0
    assert m1["win_rate"] == 1.0

    # Third point: small loss -> win_rate decreases
    _, m2 = series[2]
    assert m2["realized_pnl"] == 5.0  # unchanged
    assert 0.0 <= (m2["win_rate"] or 0.0) <= 1.0

    # Sharpe should be finite from >=2 returns
    _, m3 = series[3]
    if m3["sharpe"] is not None:
        assert math.isfinite(m3["sharpe"])
