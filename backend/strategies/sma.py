"""Simple SMA crossover strategies (Nautilus-backed or placeholder).

Exposes minimal artifacts (orders, fills, equity) consumed by the app.
"""

from __future__ import annotations

from typing import Any

# We provide a real Nautilus Strategy when available, otherwise keep a lightweight placeholder
try:  # pragma: no cover - exercised in integration
    from datetime import timedelta

    from nautilus_trader.indicators.average.sma import SimpleMovingAverage  # type: ignore
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
              **kwargs: Additional options; currently supports `qty`, `rth_only`, and `eod_flat`.
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
            self.eod_flat = bool(kwargs.get("eod_flat", False))
            # Sizing policy (Epic 19 MVP)
            self.sizing_policy = str(kwargs.get("sizing_policy", "FixedQty"))
            self.sizing_params = dict(kwargs.get("sizing_params", {}))

            # Runtime state for artifact mapping (MVP, independent of engine internals)
            self._bar_type: BarType | None = None
            self._fast: SimpleMovingAverage | None = None
            self._slow: SimpleMovingAverage | None = None
            self._in_position: bool = False
            self._pos_qty: int = 0  # track current position size for equity fallback

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
            # Subscribe to 1m MID bars aggregated INTERNALLY from QuoteTicks
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            self._bar_type = BarType(self.instrument_id, spec, AggregationSource.INTERNAL)

            # Register indicators
            self._fast = SimpleMovingAverage(self.fast_period)
            self._slow = SimpleMovingAverage(self.slow_period)
            self.register_indicator_for_bars(self._bar_type, self._fast)
            self.register_indicator_for_bars(self._bar_type, self._slow)

            # Subscribe to bars (let client be inferred from instrument venue)
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
        def _compute_qty(self, px: float) -> int:
            """Compute order size based on sizing policy.

            Policies (MVP):
              - FixedQty: use self.qty
              - PercentOfEquity: qty = floor((pct * equity) / px), pct in [0,1]
              - VolTarget: fallback to FixedQty (placeholder)
            """
            try:
                pol = (self.sizing_policy or "FixedQty").lower()
            except Exception:
                pol = "fixedqty"
            if pol in ("fixedqty", "fixed_qty"):
                return max(1, int(self.qty))
            if pol in ("percentofequity", "poe", "percent_equity"):
                try:
                    pct = float(self.sizing_params.get("pct", 0.01))
                except Exception:
                    pct = 0.01
                try:
                    eq = float((self.equity[-1] or {}).get("value", 0.0)) if self.equity else float(self._compute_equity_snapshot())
                except Exception:
                    eq = float(10000.0)
                try:
                    q = int(max(1, (pct * eq) / max(0.01, float(px))))
                except Exception:
                    q = int(max(1, self.qty))
                return q
            # VolTarget and others -> fallback
            return max(1, int(self.qty))

            except Exception:
                return True, None

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
            if (
                not self._fast
                or not self._slow
                or not self._fast.initialized
                or not self._slow.initialized
            ):
                return
            f = float(self._fast.value)
            s = float(self._slow.value)
            if not self._in_position and f > s:
                self._place(OrderSide.BUY, px, ts)
            elif self._in_position and f < s:
                self._place(OrderSide.SELL, px, ts)

        def _maybe_eod_flat(self, px: float, ts, mins: int | None) -> None:
            if self.eod_flat and self._in_position and mins is not None and mins == (15 * 60 + 59):
                self._place(OrderSide.SELL, px, ts)

        def on_bar(self, bar) -> None:
            """Handle an incoming bar for this instrument and update signals."""
            # Only handle our instrument/BarType
            if self._bar_type is None or bar.bar_type != self._bar_type:
                return

            tz_ny = self._get_tz_ny()

            px = (
                float(bar.close.as_double())
                if hasattr(bar.close, "as_double")
                else float(bar.close)
            )
            ts = getattr(bar, "ts_event", None) or getattr(bar, "ts_init", None)

            in_rth, mins = self._in_rth_window(ts, tz_ny, self.rth_only)

            equity_val = self._compute_equity_snapshot()
            self.equity.append({"ts_utc": ts, "value": equity_val})

            if not in_rth:
                return

            self._maybe_signal(px, ts)
            self._maybe_eod_flat(px, ts, mins)

        # Generic event handler to catch ALL events for debugging
        def on_event(self, event) -> None:  # pragma: no cover
            """Handle a generic engine event (debug logging only)."""
            import logging

            logger = logging.getLogger("strategy.events")

            event_type = type(event).__name__

            # Log all order-related events
            if "Order" in event_type:
                logger.info(f"EVENT: {event_type} - {event}")

            # Call parent to ensure normal processing continues
            super().on_event(event)

        # Keep artifacts in sync when fills occur (best-effort; details may vary by engine)
        def on_order_filled(self, event) -> None:  # pragma: no cover
            """Handle order fill events and update local artifacts."""
            import logging

            logger = logging.getLogger("strategy.fills")

            logger.info(f"🎯 on_order_filled CALLED! Event: {event}")

            try:
                # OrderFilled event has order_side directly, not event.order.side
                side = event.order_side  # BUY/SELL enum
                px = (
                    float(event.last_px.as_double())
                    if hasattr(event, "last_px")
                    else float(event.avg_px.as_double())
                )
                qty = int(event.last_qty) if hasattr(event, "last_qty") else int(event.quantity)
                ts = getattr(event, "ts_event", None)

                # Update position tracking (simple flag for strategy logic)
                if side == OrderSide.BUY:
                    self._in_position = True
                    try:
                        self._pos_qty += qty
                    except Exception:
                        self._pos_qty = max(0, self._pos_qty + qty)
                else:  # SELL
                    try:
                        self._pos_qty -= qty
                    except Exception:
                        self._pos_qty = max(0, self._pos_qty - qty)
                    if self._pos_qty <= 0:
                        self._pos_qty = 0
                        self._in_position = False
                # Note: We rely on Nautilus for actual position/cash tracking

                # Record fill with explicit side for metrics
                fill_data = {
                    "ts_utc": ts,
                    "side": "BUY" if side == OrderSide.BUY else "SELL",
                    "order_id": str(event.client_order_id),
                    "qty": qty,
                    "price": px,
                    "fill_id": str(getattr(event, "trade_id", "unknown")),
                    "slippage": 0.0,
                    "fee": 0.0,
                }
                self.fills.append(fill_data)

                logger.info(
                    f"✅ FILL RECORDED: {fill_data['side']} {qty} @ ${px:.2f}, "
                    f"total_fills={len(self.fills)}"
                )

            except Exception as e:
                logger.error(f"❌ ERROR in on_order_filled: {type(e).__name__}: {e}")
                import traceback

                logger.error(traceback.format_exc())

        # Helper to submit a market order and record an order artifact
        def _place(self, side: OrderSide, px: float, ts) -> None:
            import logging

            logger = logging.getLogger("strategy.orders")

            from nautilus_trader.model.objects import Quantity

            qty_int = int(self._compute_qty(px))
            qty = Quantity.from_int(qty_int)
            # Changed from IOC to GTC - IOC orders may not trigger on_order_filled in backtest
            order = self.order_factory.market(
                self.instrument_id, side, qty, time_in_force=TimeInForce.GTC
            )
            self.submit_order(order)
            oid = f"naut-{self._oid_seq}"
            self._oid_seq += 1

            order_data = {
                "ts_utc": ts,
                "side": "BUY" if side == OrderSide.BUY else "SELL",
                "qty": qty_int,
                "price": px,
                "order_id": oid,
                "type": "MKT",
                "time_in_force": "GTC",
            }

            self.orders.append(order_data)

            logger.info(
                f"ORDER SUBMITTED: {order_data['side']} {qty_int} @ ${px:.2f}, "
                f"order_id={oid}, nautilus_order_id={order.client_order_id}"
            )

            # Note: Do NOT optimistically update state here
            # Wait for on_order_filled to update based on actual execution

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
