from __future__ import annotations

from typing import Any, Optional


# We provide a real Nautilus Strategy when available, otherwise keep a lightweight placeholder
try:  # pragma: no cover - exercised in integration
    from datetime import timedelta

    from nautilus_trader.trading.strategy import Strategy  # type: ignore
    from nautilus_trader.indicators.average.sma import SimpleMovingAverage  # type: ignore
    from nautilus_trader.model.data import BarType, BarSpecification  # type: ignore
    from nautilus_trader.model.identifiers import InstrumentId, ClientId  # type: ignore
    from nautilus_trader.model.enums import PriceType, AggregationSource, OrderSide, TimeInForce  # type: ignore

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

        def __init__(self, instrument_id: str, fast: int = 20, slow: int = 50, qty: int = 1, rth_only: bool = False, eod_flat: bool = False, **_: Any) -> None:
            super().__init__()
            if fast >= slow:
                fast, slow = 20, 50
            self.instrument_id_str = instrument_id
            self.instrument_id = InstrumentId.from_str(instrument_id)
            self.fast_period = int(fast)
            self.slow_period = int(slow)
            self.qty = int(qty)
            self.rth_only = bool(rth_only)
            self.eod_flat = bool(eod_flat)

            # Runtime state for artifact mapping (MVP, independent of engine internals)
            self._bar_type: Optional[BarType] = None
            self._fast: Optional[SimpleMovingAverage] = None
            self._slow: Optional[SimpleMovingAverage] = None
            self._in_position: bool = False

            self.orders: list[dict[str, Any]] = []
            self.fills: list[dict[str, Any]] = []
            self.equity: list[dict[str, Any]] = []
            self._oid_seq: int = 0

        def on_load(self) -> None:  # noqa: D401
            # Defer subscriptions to on_start per Nautilus guidance
            pass

        def on_start(self) -> None:  # noqa: D401
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

        def on_bar(self, bar) -> None:
            # Only handle our instrument/BarType
            if self._bar_type is None or bar.bar_type != self._bar_type:
                return

            # Extract timestamp and localize to NY for RTH/EOD logic
            from datetime import timezone
            try:
                from zoneinfo import ZoneInfo
                tz_ny = ZoneInfo("America/New_York")
            except Exception:
                tz_ny = None

            px = float(bar.close.as_double()) if hasattr(bar.close, 'as_double') else float(bar.close)
            ts = getattr(bar, 'ts_event', None) or getattr(bar, 'ts_init', None)

            # RTH filter: 09:30 <= time < 16:00 NY
            in_rth = True
            mins = None
            if self.rth_only and tz_ny and ts is not None:
                try:
                    local = ts.astimezone(tz_ny)
                    mins = local.hour * 60 + local.minute
                    in_rth = (mins >= 9*60 + 30) and (mins < 16*60)
                except Exception:
                    in_rth = True

            # Track equity from Nautilus portfolio (REQUIRED - no fallbacks)
            import logging
            logger = logging.getLogger("strategy.equity")

            try:
                portfolio = self.portfolio
                venue = self.instrument_id.venue  # Get venue from instrument (e.g., XNAS)
                account = portfolio.account(venue)  # Pass venue to get the account

                # Get total account value using calculated_balance which includes positions
                # This is the correct way to get total equity (cash + unrealized PnL)
                from nautilus_trader.model.currencies import USD
                equity_money = account.balance_total(USD)
                equity_val = float(equity_money.as_double())
                logger.debug(f"Equity from Nautilus balance_total(USD): ${equity_val:.2f}")

            except Exception as e:
                logger.error(f"❌ CRITICAL: Failed to get equity from Nautilus portfolio: {type(e).__name__}: {e}")
                logger.error(f"   Portfolio type: {type(self.portfolio) if hasattr(self, 'portfolio') else 'N/A'}")
                logger.error(f"   Venue: {venue if 'venue' in locals() else 'N/A'}")
                logger.error(f"   Account type: {type(account) if 'account' in locals() else 'N/A'}")
                raise RuntimeError(f"Cannot track equity without Nautilus portfolio access: {e}") from e

            self.equity.append({"ts_utc": ts, "value": equity_val})

            if not in_rth:
                # Optionally flatten if outside RTH, but we rely on EOD flatten at 15:59
                return

            if not self._fast or not self._slow or not self._fast.initialized or not self._slow.initialized:
                # Not enough history yet for signals
                # But allow EOD flatten safeguard below if needed
                pass
            else:
                f = float(self._fast.value)
                s = float(self._slow.value)

                # Generate naive crossover signals
                if not self._in_position and f > s:
                    self._place(OrderSide.BUY, px, ts)
                elif self._in_position and f < s:
                    self._place(OrderSide.SELL, px, ts)

            # End-of-day flatten at 15:59 NY
            if self.eod_flat and self._in_position and mins is not None and mins == (15*60 + 59):
                self._place(OrderSide.SELL, px, ts)

        # Generic event handler to catch ALL events for debugging
        def on_event(self, event) -> None:  # pragma: no cover
            import logging
            logger = logging.getLogger("strategy.events")

            event_type = type(event).__name__

            # Log all order-related events
            if 'Order' in event_type:
                logger.info(f"EVENT: {event_type} - {event}")

            # Call parent to ensure normal processing continues
            super().on_event(event)

        # Keep artifacts in sync when fills occur (best-effort; details may vary by engine)
        def on_order_filled(self, event) -> None:  # pragma: no cover
            import logging
            logger = logging.getLogger("strategy.fills")

            logger.info(f"🎯 on_order_filled CALLED! Event: {event}")

            try:
                # OrderFilled event has order_side directly, not event.order.side
                side = event.order_side  # BUY/SELL enum
                px = float(event.last_px.as_double()) if hasattr(event, 'last_px') else float(event.avg_px.as_double())
                qty = int(event.last_qty) if hasattr(event, 'last_qty') else int(event.quantity)
                ts = getattr(event, 'ts_event', None)

                # Update position tracking (simple flag for strategy logic)
                if side == OrderSide.BUY:
                    self._in_position = True
                # Note: We rely on Nautilus for actual position/cash tracking

                # Record fill with explicit side for metrics
                fill_data = {
                    "ts_utc": ts,
                    "side": "BUY" if side == OrderSide.BUY else "SELL",
                    "order_id": str(event.client_order_id),
                    "qty": qty,
                    "price": px,
                    "fill_id": str(getattr(event, 'trade_id', 'unknown')),
                    "slippage": 0.0,
                    "fee": 0.0,
                }
                self.fills.append(fill_data)

                logger.info(
                    f"✅ FILL RECORDED: {fill_data['side']} {qty} @ ${px:.2f}, total_fills={len(self.fills)}"
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
            qty_int = int(self.qty)
            qty = Quantity.from_int(qty_int)
            # Changed from IOC to GTC - IOC orders may not trigger on_order_filled in backtest
            order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.GTC)
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
                "time_in_force": "GTC"
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
            if fast >= slow:
                fast, slow = 20, 50
            self.fast = int(fast)
            self.slow = int(slow)

        def __repr__(self) -> str:
            return f"SMAStrategy(fast={self.fast}, slow={self.slow})"

