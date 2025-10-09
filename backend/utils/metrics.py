import math
from typing import Any

from backend.utils.datetime import normalize_timestamp


def _annualization_factor(
    bar_minutes: int, minutes_per_session: int = 390, sessions_per_year: int = 252
) -> float:
    if bar_minutes <= 0:
        return float("nan")
    periods_per_session = max(1, int(minutes_per_session / bar_minutes))
    return float(periods_per_session * sessions_per_year)



def _preprocess_realized_epochs(realized_series: list[tuple[str, float]]) -> list[tuple[int, float]]:
    epochs: list[tuple[int, float]] = []
    for ts_iso, val in realized_series or []:
        try:
            ep, _ = normalize_timestamp(ts_iso)
            epochs.append((ep, float(val)))
        except Exception:
            continue
    return epochs


def _advance_realized(
    realized_epochs: list[tuple[int, float]],
    realized_idx: int,
    last_realized_val: float | None,
    epoch: int,
    wins: int,
    losses: int,
) -> tuple[int, float | None, int, int]:
    while (realized_idx + 1) < len(realized_epochs) and realized_epochs[realized_idx + 1][0] <= epoch:
        next_val = realized_epochs[realized_idx + 1][1]
        delta = next_val - (last_realized_val if last_realized_val is not None else 0.0)
        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        last_realized_val = next_val
        realized_idx += 1
    return realized_idx, last_realized_val, wins, losses


def _calc_returns(prev_val: float | None, v_cur: float | None) -> tuple[float | None, float | None]:
    if v_cur is None:
        return None, prev_val
    if prev_val is not None and prev_val != 0:
        r_cur = (v_cur / prev_val) - 1.0
    else:
        r_cur = None
    return r_cur, v_cur


def _calc_total_return(base_val: float | None, v_cur: float | None) -> float | None:
    if base_val is None or base_val == 0 or v_cur is None:
        return None
    return (v_cur / base_val) - 1.0


def _update_peak_drawdown(peak: float | None, v_cur: float | None) -> tuple[float | None, float | None]:
    if v_cur is None:
        return peak, None
    if peak is None or v_cur > peak:
        peak = v_cur
    drawdown = None if peak in (None, 0) else max(0.0, (peak - v_cur) / peak)
    return peak, drawdown


def _update_sharpe_state(
    r_cur: float | None,
    returns_sum: float,
    returns_sq_sum: float,
    n_returns: int,
    P: float,
) -> tuple[float, float, int, float | None]:
    sharpe: float | None = None
    if r_cur is not None:
        n_returns += 1
        returns_sum += r_cur
        returns_sq_sum += r_cur * r_cur
        mean = returns_sum / n_returns
        var = max(0.0, (returns_sq_sum / n_returns) - (mean * mean))
        std = math.sqrt(var)
        if std > 0 and P > 0 and math.isfinite(P):
            sharpe = math.sqrt(P) * (mean / std)
    return returns_sum, returns_sq_sum, n_returns, sharpe


def compute_cumulative_metrics(
    equity_rows: list[dict[str, Any]],
    realized_series: list[tuple[str, float]],
    *,
    bar_minutes: int = 1,
    minutes_per_session: int = 390,
    sessions_per_year: int = 252,
) -> list[tuple[str, dict[str, float | None]]]:
    """
    Compute cumulative-to-date metrics aligned to equity timestamps.

    Inputs:
      - equity_rows: list of {"ts": ISO, "value": float}
      - realized_series: list of (ISO, value) cumulative realized PnL in USD

    Returns:
      - list of (ISO, metrics_dict) where metrics_dict has keys:
        equity, return, realized_pnl, total_return, drawdown, sharpe, win_rate
    """
    out: list[tuple[str, dict[str, float | None]]] = []

    if not equity_rows:
        return out

    # Prepare realized pointer and preprocessed epochs
    realized_idx = -1
    last_realized_val: float | None = None
    wins = 0
    losses = 0

    realized_epochs = _preprocess_realized_epochs(realized_series)

    # Running stats for Sharpe
    returns_sum = 0.0
    returns_sq_sum = 0.0
    n_returns = 0

    # First equity for total return baseline
    base_val = float(equity_rows[0]["value"]) if equity_rows and "value" in equity_rows[0] else None
    prev_val: float | None = None

    P = _annualization_factor(bar_minutes, minutes_per_session, sessions_per_year)

    for er in equity_rows:
        # Canonical: expect ts_utc only to avoid hidden fallbacks
        ts = er.get("ts_utc")
        if ts is None:
            continue
        try:
            epoch, iso = normalize_timestamp(ts)
        except Exception:
            continue

        # Advance realized pointer to <= current epoch
        realized_idx, last_realized_val, wins, losses = _advance_realized(
            realized_epochs, realized_idx, last_realized_val, epoch, wins, losses
        )

        # Returns + totals
        v_cur = None
        try:
            v_cur = float(er["value"])  # may raise
        except Exception:
            v_cur = None
        r_cur, prev_val = _calc_returns(prev_val, v_cur)
        total_ret = _calc_total_return(base_val, v_cur)

        # Drawdown relative to running peak (per-call state)
        if "peak" not in locals():
            peak = None  # type: ignore[assignment]
        peak, drawdown = _update_peak_drawdown(peak, v_cur)

        # Sharpe (cumulative)
        returns_sum, returns_sq_sum, n_returns, sharpe = _update_sharpe_state(
            r_cur, returns_sum, returns_sq_sum, n_returns, P
        )

        # Win rate
        win_rate = (wins / (wins + losses)) if (wins + losses) > 0 else None

        out.append(
            (
                iso,
                {
                    "equity": float(er.get("value")) if er.get("value") is not None else None,
                    "return": r_cur,
                    "realized_pnl": last_realized_val,
                    "total_return": total_ret,
                    "drawdown": drawdown,
                    "sharpe": sharpe,
                    "win_rate": win_rate,
                },
            )
        )

    return out
