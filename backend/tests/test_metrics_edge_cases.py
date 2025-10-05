import math
import pytest

from backend.utils.metrics import compute_cumulative_metrics


def test_sharpe_null_when_std_zero():
    # Equity flat -> all returns zero -> std = 0 => sharpe is None
    equity = [
        {"ts": "2024-01-01T00:00:00Z", "value": 100.0},
        {"ts": "2024-01-01T00:01:00Z", "value": 100.0},
        {"ts": "2024-01-01T00:02:00Z", "value": 100.0},
        {"ts": "2024-01-01T00:03:00Z", "value": 100.0},
    ]
    series = compute_cumulative_metrics(equity, realized_series=[], bar_minutes=1)
    # At last point, sharpe should be None
    _, m_last = series[-1]
    assert m_last["sharpe"] is None


def test_win_rate_ignores_zero_deltas():
    equity = [
        {"ts": "2024-01-01T00:00:00Z", "value": 100.0},
        {"ts": "2024-01-01T00:01:00Z", "value": 101.0},
    ]
    # Realized PnL goes 0 -> 0 -> 3 (one zero delta, then +3)
    realized = [("2024-01-01T00:00:00Z", 0.0), ("2024-01-01T00:00:30Z", 0.0), ("2024-01-01T00:01:00Z", 3.0)]
    series = compute_cumulative_metrics(equity, realized_series=realized, bar_minutes=1)
    # On last point, win_rate counts only >0 or <0 deltas (one positive -> 1/1)
    _, m_last = series[-1]
    assert m_last["win_rate"] == pytest.approx(1.0)

