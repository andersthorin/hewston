import math
from backend.services.streamer import _precompute_metrics_from_equity


def test_precompute_metrics_basic_series():
    rows = [
        {"ts_utc": "2024-01-01T00:00:00Z", "value": 100.0},
        {"ts_utc": "2024-01-01T00:01:00Z", "value": 110.0},
        {"ts_utc": "2024-01-01T00:02:00Z", "value": 105.0},
        {"ts_utc": "2024-01-01T00:03:00Z", "value": 120.0},
    ]
    m = _precompute_metrics_from_equity(rows)

    trs = m["total_return_so_far"]
    mdd = m["max_drawdown_so_far"]
    shp = m["sharpe_so_far"]

    # total return so far
    assert trs[0] is not None and abs(trs[0] - 0.0) < 1e-12
    assert trs[1] is not None and abs(trs[1] - 0.10) < 1e-6
    assert trs[-1] is not None and abs(trs[-1] - 0.20) < 1e-6  # 120/100 - 1

    # drawdown is non-decreasing and within [0,1]
    prev = 0.0
    for v in mdd:
        if v is None:
            continue
        assert 0.0 <= v <= 1.0
        assert v + 1e-12 >= prev
        prev = v

    # sharpe first element is None; later can be None or finite number
    assert shp[0] is None
    assert shp[1] is None or math.isfinite(shp[1])
    assert shp[2] is None or math.isfinite(shp[2])


def test_precompute_handles_zeros_and_nans():
    rows = [
        {"ts_utc": "2024-01-01T00:00:00Z", "value": 0.0},
        {"ts_utc": "2024-01-01T00:01:00Z", "value": 0.0},
        {"ts_utc": "2024-01-01T00:02:00Z", "value": 1.0},
    ]
    m = _precompute_metrics_from_equity(rows)
    # total return undefined when base is zero
    assert m["total_return_so_far"][0] is None
    # mdd should be defined (peak tracking), stays at 0 for flat zeros, then becomes 0 when peak rises
    assert m["max_drawdown_so_far"][0] in (None, 0.0)
    # sharpe may be None when insufficient or zero variance
    assert m["sharpe_so_far"][1] is None
