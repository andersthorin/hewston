from __future__ import annotations

from typing import Any, Dict, List


class MetricsCalculator:
    def calculate_metrics(self, backtest_result: Any) -> Dict[str, float]:  # pragma: no cover (interface)
        raise NotImplementedError


class StandardMetricsCalculator(MetricsCalculator):
    """MVP metrics: total_return and win_rate.

    Accepts either a dict with keys 'equity' and 'fills' or explicit lists.
    """

    def calculate_metrics(
        self,
        backtest_result: Dict[str, Any] | None = None,
        *,
        equity: List[Dict[str, Any]] | None = None,
        fills: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, float]:
        if backtest_result is not None:
            equity = backtest_result.get("equity", [])
            fills = backtest_result.get("fills", [])
        equity = equity or []
        fills = fills or []

        total_return = 0.0
        if equity:
            start = float(equity[0].get("value", 0.0) or 0.0)
            end = float(equity[-1].get("value", 0.0) or 0.0)
            total_return = (end - start) / start if start else 0.0

        # Max drawdown (as negative fraction, e.g., -0.08 for -8%) from equity curve
        max_drawdown = 0.0
        if equity:
            peak = None  # type: float | None
            min_drawdown = 0.0
            for pt in equity:
                try:
                    v = float(pt.get("value", 0.0) or 0.0)
                except Exception:
                    v = 0.0
                if peak is None or v > peak:
                    peak = v
                if peak and peak > 0:
                    dd = (v - peak) / peak  # <= 0
                    if dd < min_drawdown:
                        min_drawdown = dd
            max_drawdown = float(min_drawdown)

        # Simple trade pairing for win rate: detect entry/exit from fills side
        wins = 0
        total = 0
        pos = 0
        entry_price = 0.0
        for f in fills:
            side = f.get("side") or f.get("Side") or None
            px = float(f.get("price", 0.0))
            qty = float(f.get("qty", 0.0))
            if side == "BUY" and pos == 0:
                pos = 1
                entry_price = px
            elif side == "SELL" and pos == 1:
                pos = 0
                pnl = (px - entry_price) * qty
                total += 1
                if pnl > 0:
                    wins += 1
        win_rate = (wins / total) if total else 0.0

        return {
            "total_return": float(total_return),
            "win_rate": float(win_rate),
            "max_drawdown": float(max_drawdown),
        }

