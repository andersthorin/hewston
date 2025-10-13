"""Simple SMA crossover strategies (Nautilus-backed or placeholder).

Exposes minimal artifacts (orders, fills, equity) consumed by the app.
"""

from __future__ import annotations

from typing import Any

# We provide a real Nautilus Strategy when available, otherwise keep a lightweight placeholder
try:  # pragma: no cover - exercised in integration
    from datetime import timedelta

    from nautilus_trader.indicators.average.sma import SimpleMovingAverage  # type: ignore
    from nautilus_trader.indicators.atr import AverageTrueRange  # type: ignore
    from nautilus_trader.indicators.dm import DirectionalMovement  # type: ignore
    from nautilus_trader.model.data import BarSpecification, BarType  # type: ignore
    from nautilus_trader.model.enums import (  # type: ignore
        AggregationSource,
        OrderSide,
        PriceType,
        TimeInForce,
    )
    from nautilus_trader.model.identifiers import InstrumentId  # type: ignore
    from nautilus_trader.trading.strategy import Strategy  # type: ignore

    class SMAStrategy(Strategy):  # type: ignore[misc]
        """Simple SMA crossover strategy using Nautilus Strategy API.

        Parameters
        - instrument_id: str like "AAPL.XNAS"
        - fast: int, short SMA period
        - slow: int, long SMA period
        - qty: int, fixed position size per signal
        - rth_only: bool, ignore pre/post-market bars
        - eod_flat: bool, force flatten at end of RTH day
        """

        def __init__(
            self,
            instrument_id: str,
            fast: int = 20,
            slow: int = 50,
            **kwargs: Any,
        ) -> None:
            """Initialize SMA crossover strategy.

            Args:
              instrument_id: Instrument like "AAPL.XNAS".
              fast: Short SMA period.
              slow: Long SMA period.
              qty: Fixed order quantity per signal.
              rth_only: If True, ignore pre/post-market bars.
              eod_flat: If True, flatten at end of RTH.
              **kwargs: Supports: qty, rth_only, eod_flat, sizing_policy, sizing_params,
                        atr_period, atr_stop_mult, risk_pct, dm_period, di_gap_min,
                        band_k, slow_slope_min, cooldown_bars, trailing_stop.
            """
            super().__init__()
            if fast >= slow:
                fast, slow = 20, 50
            self.instrument_id_str = instrument_id
            self.instrument_id = InstrumentId.from_str(instrument_id)
            self.fast_period = int(fast)
            self.slow_period = int(slow)
            # Extract known options from kwargs (backward-compatible)
            self.qty = int(kwargs.get("qty", 1))
            self.rth_only = bool(kwargs.get("rth_only", False))
            # Default to eod_flat=True per project directive
            self.eod_flat = bool(kwargs.get("eod_flat", True))
            # Sizing policy: FixedQty | PercentOfEquity | RiskATR
            self.sizing_policy = str(kwargs.get("sizing_policy", "FixedQty"))
            self.sizing_params = dict(kwargs.get("sizing_params", {}))
            # Risk / filters params
            self.atr_period = int(kwargs.get("atr_period", 14))
            self.atr_stop_mult = float(kwargs.get("atr_stop_mult", 1.5))
            self.risk_pct = float(kwargs.get("risk_pct", 0.005))  # 0.5% default
            self.dm_period = int(kwargs.get("dm_period", 14))
            self.di_gap_min = float(kwargs.get("di_gap_min", 5.0))  # DI+ - DI- gap in points
            self.band_k = float(kwargs.get("band_k", 0.25))  # band in ATRs
            self.slow_slope_min = float(kwargs.get("slow_slope_min", 0.0))
            self.cooldown_bars = int(kwargs.get("cooldown_bars", 10))
            self.trailing_stop = bool(kwargs.get("trailing_stop", False))
            self.max_notional_pct = float(kwargs.get("max_notional_pct", 0.20))  # cap notional to % of equity


            # Runtime state for artifact mapping (MVP, independent of engine internals)
            self._bar_type: BarType | None = None
            self._fast: SimpleMovingAverage | None = None
            self._slow: SimpleMovingAverage | None = None
            self._atr: AverageTrueRange | None = None
            self._dm: DirectionalMovement | None = None
            self._prev_diff: float | None = None
            self._prev_slow: float | None = None
            self._cooldown: int = 0
            self._in_position: bool = False
            self._pos_qty: int = 0
            self._entry_px: float | None = None
            self._stop_px: float | None = None

            self.orders: list[dict[str, Any]] = []
            self.fills: list[dict[str, Any]] = []
            self.equity: list[dict[str, Any]] = []
            self._oid_seq: int = 0

        def on_load(self) -> None:  # noqa: D401
            """Hook called when strategy is loaded."""
            # Defer subscriptions to on_start per Nautilus guidance
            pass

        def on_start(self) -> None:  # noqa: D401
            """Hook called when the strategy starts; subscribe and init indicators."""
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            self._bar_type = BarType(self.instrument_id, spec, AggregationSource.INTERNAL)

            # Register indicators (ensure registration before requesting/subscribing)
            self._fast = SimpleMovingAverage(self.fast_period)
            self._slow = SimpleMovingAverage(self.slow_period)
            self._atr = AverageTrueRange(self.atr_period)
            self._dm = DirectionalMovement(self.dm_period)
            self.register_indicator_for_bars(self._bar_type, self._fast)
            self.register_indicator_for_bars(self._bar_type, self._slow)
            self.register_indicator_for_bars(self._bar_type, self._atr)
            self.register_indicator_for_bars(self._bar_type, self._dm)

            # Subscribe to bars
            self.subscribe_bars(self._bar_type)

        def _get_tz_ny(self):
            try:  # pragma: no cover
                from zoneinfo import ZoneInfo

                return ZoneInfo("America/New_York")
            except Exception:
                return None

        def _in_rth_window(self, ts, tz_ny, rth_only: bool) -> tuple[bool, int | None]:
            if not rth_only or tz_ny is None or ts is None:
                return True, None
            try:
                local = ts.astimezone(tz_ny)
                mins = local.hour * 60 + local.minute
                return ((mins >= 9 * 60 + 30) and (mins < 16 * 60)), mins
            except Exception:
                return True, None
        def _compute_qty(self, px: float) -> int:
            """Compute order size based on sizing policy with a notional cap.

            Policies:
              - FixedQty: use self.qty (capped by notional)
              - PercentOfEquity: qty = floor((pct * equity) / px), pct in [0,1]
              - RiskATR: qty = floor((risk_pct * equity) / (atr_stop_mult * ATR))
            """
            try:
                pol = (self.sizing_policy or "FixedQty").lower()
            except Exception:
                pol = "fixedqty"

            # Obtain equity and compute a cap based on max notional percentage
            try:
                eq = float((self.equity[-1] or {}).get("value", 0.0)) if self.equity else float(self._compute_equity_snapshot())
            except Exception:
                eq = float(10000.0)
            pxv = max(0.01, float(px))
            try:
                cap_pct = float(getattr(self, "max_notional_pct", 0.20))
            except Exception:
                cap_pct = 0.20
            q_cap = int(max(1, (cap_pct * eq) / pxv))

            if pol in ("fixedqty", "fixed_qty"):
                return int(max(1, min(int(self.qty), q_cap)))

            if pol in ("percentofequity", "poe", "percent_equity"):
                try:
                    pct = float(self.sizing_params.get("pct", 0.01))
                except Exception:
                    pct = 0.01
                q_raw = int(max(1, (pct * eq) / pxv))
                return int(max(1, min(q_raw, q_cap)))

            if pol in ("riskatr", "risk_atr"):
                if not self._atr or not self._atr.initialized:
                    return int(max(1, min(int(self.qty), q_cap)))
                risk_pct = float(self.risk_pct)
                atr_val = max(1e-6, float(self._atr.value))
                denom = max(0.01, float(self.atr_stop_mult) * atr_val)
                q_raw = int(max(1, (risk_pct * eq) / denom))
                return int(max(1, min(q_raw, q_cap)))

            return int(max(1, min(int(self.qty), q_cap)))

        def _filters_ok(self) -> bool:
            if not self._fast or not self._slow or not self._atr or not self._dm:
                return False
            if not (self._fast.initialized and self._slow.initialized and self._atr.initialized and self._dm.initialized):
                return False
            # Slow slope filter
            try:
                s = float(self._slow.value)
                ps = float(self._prev_slow) if self._prev_slow is not None else s
                slope = s - ps
                if slope < float(self.slow_slope_min):
                    return False
            except Exception:
                return False
            # Directional movement filter: require DI+ - DI- gap
            try:
                gap = float(self._dm.pos - self._dm.neg)
                if gap < float(self.di_gap_min):
                    return False
            except Exception:
                return False
            return True

        def _update_trailing_stop(self, px: float) -> None:
            if not self._in_position or not self._atr or not self._atr.initialized:
                return
            if not self.trailing_stop:
                return
            try:
                candidate = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                if self._stop_px is None or candidate > float(self._stop_px):
                    self._stop_px = candidate
            except Exception:
                return

        def _compute_equity_snapshot(self) -> float:
            import logging

            logger = logging.getLogger("strategy.equity")
            try:
                portfolio = self.portfolio
                venue = self.instrument_id.venue
                account = portfolio.account(venue)
                from nautilus_trader.model.currencies import USD

                bal_money = account.balance_total(USD)
                bal_val = (
                    float(bal_money.as_double())
                    if hasattr(bal_money, "as_double")
                    else float(bal_money)
                )
                upnls = portfolio.unrealized_pnls(venue)
                upnl_money = upnls.get(USD)
                upnl_val = (
                    float(upnl_money.as_double())
                    if (upnl_money is not None and hasattr(upnl_money, "as_double"))
                    else float(upnl_money or 0.0)
                )
                equity_val = bal_val + upnl_val
                logger.debug(
                    f"Equity snapshot: cash={bal_val:.2f}, upnl={upnl_val:.2f}, eq={equity_val:.2f}"
                )
                return float(equity_val)
            except Exception as e:  # pragma: no cover
                logger.error(
                    "❌ CRITICAL: Failed to obtain canonical equity "
                    "(balance_total + unrealized_pnls): "
                    f"{type(e).__name__}: {e}"
                )
                raise RuntimeError(f"Canonical equity unavailable from Nautilus: {e}") from e

        def _maybe_signal(self, px: float, ts) -> None:
            if not (self._fast and self._slow and self._atr and self._dm):
                return
            if not (self._fast.initialized and self._slow.initialized and self._atr.initialized and self._dm.initialized):
                return
            f = float(self._fast.value); s = float(self._slow.value)
            diff = f - s
            # Cross detection
            prev = float(self._prev_diff) if self._prev_diff is not None else 0.0
            crossed_up = prev <= 0.0 and diff > 0.0
            crossed_down = prev >= 0.0 and diff < 0.0
            band_ok = abs(diff) >= float(self.band_k) * float(self._atr.value)
            if self._cooldown > 0:
                return
            if not self._in_position and crossed_up and band_ok and self._filters_ok():
                # set stop
                self._entry_px = float(px)
                self._stop_px = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                self._place(OrderSide.BUY, px, ts)
            elif self._in_position and crossed_down:
                self._place(OrderSide.SELL, px, ts)
            self._prev_diff = diff
            self._prev_slow = s

        def _maybe_eod_flat(self, px: float, ts, mins: int | None) -> None:
            if self.eod_flat and self._in_position and mins is not None and mins == (15 * 60 + 59):
                self._place(OrderSide.SELL, px, ts)

        def on_bar(self, bar) -> None:
            """Handle an incoming bar for this instrument and update signals."""
            if self._bar_type is None or bar.bar_type != self._bar_type:
                return
            tz_ny = self._get_tz_ny()
            px = float(bar.close.as_double()) if hasattr(bar.close, "as_double") else float(bar.close)
            ts = getattr(bar, "ts_event", None) or getattr(bar, "ts_init", None)
            in_rth, mins = self._in_rth_window(ts, tz_ny, self.rth_only)
            equity_val = self._compute_equity_snapshot()
            self.equity.append({"ts_utc": ts, "value": equity_val})
            # Stop check first
            if self._in_position and self._stop_px is not None and px <= float(self._stop_px):
                self._place(OrderSide.SELL, px, ts)
                self._cooldown = self.cooldown_bars
                self._entry_px = None; self._stop_px = None
            # Trailing stop update (if any)
            self._update_trailing_stop(px)
            if not in_rth:
                return
            # Cooldown decrement
            if self._cooldown > 0:
                self._cooldown -= 1
                return
            self._maybe_signal(px, ts)
            self._maybe_eod_flat(px, ts, mins)

        # Generic event handler to catch ALL events for debugging
        def on_event(self, event) -> None:  # pragma: no cover
            import logging
            logger = logging.getLogger("strategy.events")
            if "Order" in type(event).__name__:
                logger.info(f"EVENT: {type(event).__name__} - {event}")
            super().on_event(event)

        # Keep artifacts in sync when fills occur
        def on_order_filled(self, event) -> None:  # pragma: no cover
            import logging
            logger = logging.getLogger("strategy.fills")
            try:
                side = event.order_side
                px = float(event.last_px.as_double()) if hasattr(event, "last_px") else float(event.avg_px.as_double())
                qty = int(event.last_qty) if hasattr(event, "last_qty") else int(event.quantity)
                ts = getattr(event, "ts_event", None)
                if side == OrderSide.BUY:
                    self._in_position = True
                    self._pos_qty = max(0, self._pos_qty + qty)
                else:
                    self._pos_qty = max(0, self._pos_qty - qty)
                    if self._pos_qty <= 0:
                        self._pos_qty = 0
                        self._in_position = False
                        self._cooldown = self.cooldown_bars
                        self._entry_px = None; self._stop_px = None
                self.fills.append({
                    "ts_utc": ts,
                    "side": "BUY" if side == OrderSide.BUY else "SELL",
                    "order_id": str(event.client_order_id),
                    "qty": qty,
                    "price": px,
                    "fill_id": str(getattr(event, "trade_id", "unknown")),
                    "slippage": 0.0,
                    "fee": 0.0,
                })
            except Exception as e:
                logger.error(f"on_order_filled error: {e}")

        # Helper to submit a market order and record an order artifact
        def _place(self, side: OrderSide, px: float, ts) -> None:
            from nautilus_trader.model.objects import Quantity
            # On exits, submit reduce-only and size to current position to avoid unintended shorts
            reduce_only = bool(side == OrderSide.SELL and getattr(self, "_in_position", False) and int(getattr(self, "_pos_qty", 0)) > 0)
            qty_int = int(self._pos_qty) if reduce_only else int(self._compute_qty(px))
            if qty_int <= 0:
                return
            qty = Quantity.from_int(qty_int)
            try:
                if reduce_only:
                    order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.GTC, reduce_only=True)
                else:
                    order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.GTC)
            except TypeError:
                order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.GTC)
            self.submit_order(order)
            oid = f"naut-{self._oid_seq}"; self._oid_seq += 1
            self.orders.append({
                "ts_utc": ts,
                "side": "BUY" if side == OrderSide.BUY else "SELL",
                "qty": qty_int,
                "price": px,
                "order_id": oid,
                "type": "MKT",
                "time_in_force": "GTC",
                "reduce_only": reduce_only,
            })

except Exception:  # pragma: no cover - fallback placeholder when Nautilus not installed

    class SMAStrategy:
        """Placeholder which only stores parameters when Nautilus is not available."""

        def __init__(self, fast: int = 20, slow: int = 50, **_: Any) -> None:
            """Initialize placeholder parameters when Nautilus is unavailable.

            Args:
              fast: Short SMA period.
              slow: Long SMA period.
            """
            """Return debug representation."""

            if fast >= slow:
                fast, slow = 20, 50
            self.fast = int(fast)
            self.slow = int(slow)

        def __repr__(self) -> str:
            """Return debug representation."""
            return f"SMAStrategy(fast={self.fast}, slow={self.slow})"
