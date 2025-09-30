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
            self._cash: float = 10_000.0
            self._units: int = 0

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

            # Track equity
            equity_val = self._cash + self._units * px
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

        # Keep artifacts in sync when fills occur (best-effort; details may vary by engine)
        def on_order_filled(self, event) -> None:  # pragma: no cover
            try:
                side = event.order.side  # BUY/SELL
                px = float(event.fill.avg_px.as_double()) if hasattr(event.fill.avg_px, 'as_double') else float(event.fill.avg_px)
                qty = int(event.fill.qty)
                ts = getattr(event, 'ts_event', None)
                if side == OrderSide.BUY:
                    self._units += qty
                    self._cash -= px * qty
                    self._in_position = True
                else:
                    self._units -= qty
                    self._cash += px * qty
                    self._in_position = self._units > 0
                # Record fill with explicit side for metrics
                self.fills.append({
                    "ts_utc": ts,
                    "side": "BUY" if side == OrderSide.BUY else "SELL",
                    "order_id": getattr(event.order, 'client_order_id', None),
                    "qty": qty,
                    "price": px,
                    "fill_id": getattr(event, 'fill_id', None),
                    "slippage": 0.0,
                    "fee": 0.0,
                })
            except Exception:
                pass

        # Helper to submit a market order and record an order artifact
        def _place(self, side: OrderSide, px: float, ts) -> None:
            from nautilus_trader.model.objects import Quantity
            qty_int = int(self.qty)
            qty = Quantity.from_int(qty_int)
            order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.IOC)
            self.submit_order(order)
            oid = f"naut-{self._oid_seq}"
            self._oid_seq += 1
            self.orders.append({"ts_utc": ts, "side": "BUY" if side == OrderSide.BUY else "SELL", "qty": qty_int, "price": px, "order_id": oid, "type": "MKT", "time_in_force": "IOC"})
            # Optimistically update our state; on_order_filled will reconcile after
            if side == OrderSide.BUY:
                self._in_position = True
            else:
                self._in_position = False

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

