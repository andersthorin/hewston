"""MomentumStrategy (Epic 17)

Simple momentum using price above/below a single SMA window.
- Emits BUY when close > SMA(window), SELL when in position and close < SMA(window)
- Shares artifact shape with SMAStrategy (orders, fills, equity)
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - integration path
    from datetime import timedelta

    from nautilus_trader.indicators.average.sma import SimpleMovingAverage  # type: ignore
    from nautilus_trader.model.data import BarSpecification, BarType  # type: ignore
    from nautilus_trader.model.enums import AggregationSource, OrderSide, PriceType, TimeInForce  # type: ignore
    from nautilus_trader.model.identifiers import InstrumentId  # type: ignore
    from nautilus_trader.trading.strategy import Strategy  # type: ignore

    class MomentumStrategy(Strategy):  # type: ignore[misc]
        def __init__(self, instrument_id: str, window: int = 20, **kwargs: Any) -> None:
            super().__init__()
            self.instrument_id_str = instrument_id
            self.instrument_id = InstrumentId.from_str(instrument_id)
            self.window = int(max(2, window))
            self.qty = int(kwargs.get("qty", 1))
            self.rth_only = bool(kwargs.get("rth_only", False))
            self.eod_flat = bool(kwargs.get("eod_flat", False))
            self.sizing_policy = str(kwargs.get("sizing_policy", "FixedQty"))
            self.sizing_params = dict(kwargs.get("sizing_params", {}))

            self._bar_type: BarType | None = None
            self._sma: SimpleMovingAverage | None = None
            self._in_position: bool = False
            self._pos_qty: int = 0
            self.orders: list[dict[str, Any]] = []
            self.fills: list[dict[str, Any]] = []
            self.equity: list[dict[str, Any]] = []
            self._oid_seq = 0

        def on_start(self) -> None:
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            self._bar_type = BarType(self.instrument_id, spec, AggregationSource.INTERNAL)
            self._sma = SimpleMovingAverage(self.window)
            self.register_indicator_for_bars(self._bar_type, self._sma)
            self.subscribe_bars(self._bar_type)

        def _get_tz_ny(self):
            try:
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

        def _compute_equity_snapshot(self) -> float:
            try:
                portfolio = self.portfolio
                venue = self.instrument_id.venue
                account = portfolio.account(venue)
                from nautilus_trader.model.currencies import USD

                bal_money = account.balance_total(USD)
                bal_val = float(bal_money.as_double()) if hasattr(bal_money, "as_double") else float(bal_money)
                upnl_money = portfolio.unrealized_pnls(venue).get(USD)
                upnl_val = float(upnl_money.as_double()) if (upnl_money is not None and hasattr(upnl_money, "as_double")) else float(upnl_money or 0.0)
                return float(bal_val + upnl_val)
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"Canonical equity unavailable: {e}") from e

        def _compute_qty(self, px: float) -> int:
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
            return max(1, int(self.qty))

        def _place(self, side: OrderSide, px: float, ts) -> None:
            from nautilus_trader.model.objects import Quantity

            qty_int = int(self._compute_qty(px))
            qty = Quantity.from_int(qty_int)
            order = self.order_factory.market(self.instrument_id, side, qty, time_in_force=TimeInForce.GTC)
            self.submit_order(order)
            oid = f"naut-{self._oid_seq}"; self._oid_seq += 1
            self.orders.append({"ts_utc": ts, "side": "BUY" if side == OrderSide.BUY else "SELL", "qty": qty_int, "price": px, "order_id": oid, "type": "MKT", "time_in_force": "GTC"})

        def on_order_filled(self, event) -> None:  # pragma: no cover
            side = event.order_side
            px = float(event.last_px.as_double()) if hasattr(event, "last_px") else float(event.avg_px.as_double())
            qty = int(event.last_qty) if hasattr(event, "last_qty") else int(event.quantity)
            ts = getattr(event, "ts_event", None)
            if side == OrderSide.BUY:
                self._in_position = True
                try:
                    self._pos_qty += qty
                except Exception:
                    self._pos_qty = max(0, self._pos_qty + qty)
            else:
                try:
                    self._pos_qty -= qty
                except Exception:
                    self._pos_qty = max(0, self._pos_qty - qty)
                if self._pos_qty <= 0:
                    self._pos_qty = 0; self._in_position = False
            self.fills.append({"ts_utc": ts, "side": "BUY" if side == OrderSide.BUY else "SELL", "order_id": str(event.client_order_id), "qty": qty, "price": px, "fill_id": str(getattr(event, "trade_id", "unknown")), "slippage": 0.0, "fee": 0.0})

        def on_bar(self, bar) -> None:
            if self._bar_type is None or bar.bar_type != self._bar_type:
                return
            tz_ny = self._get_tz_ny()
            px = float(bar.close.as_double()) if hasattr(bar.close, "as_double") else float(bar.close)
            ts = getattr(bar, "ts_event", None) or getattr(bar, "ts_init", None)
            in_rth, mins = self._in_rth_window(ts, tz_ny, self.rth_only)
            # equity track
            self.equity.append({"ts_utc": ts, "value": float(self._compute_equity_snapshot())})
            if not in_rth:
                return
            if self._sma and self._sma.initialized:
                m = float(self._sma.value)
                if (not self._in_position) and px > m:
                    self._place(OrderSide.BUY, px, ts)
                elif self._in_position and px < m:
                    self._place(OrderSide.SELL, px, ts)

except Exception:  # pragma: no cover - placeholder when Nautilus not installed

    class MomentumStrategy:
        def __init__(self, instrument_id: str, window: int = 20, **_: Any) -> None:
            self.instrument_id = instrument_id
            self.window = int(window)

        def __repr__(self) -> str:  # debug-only
            return f"MomentumStrategy(window={self.window}, instrument_id={self.instrument_id})"

