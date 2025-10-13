"""RSIMeanReversionStrategy (Epic 17)

Basic RSI mean-reversion:
- BUY when RSI < oversold; SELL (flatten) when RSI > overbought
- Uses 14-period RSI by default
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover
    from datetime import timedelta

    from nautilus_trader.model.data import BarSpecification, BarType  # type: ignore
    from nautilus_trader.model.enums import AggregationSource, OrderSide, PriceType, TimeInForce  # type: ignore
    from nautilus_trader.model.identifiers import InstrumentId  # type: ignore
    from nautilus_trader.trading.strategy import Strategy  # type: ignore
    from nautilus_trader.indicators.rsi import RelativeStrengthIndex  # type: ignore
    from nautilus_trader.indicators.atr import AverageTrueRange  # type: ignore
    from nautilus_trader.indicators.dm import DirectionalMovement  # type: ignore

    # Using Nautilus RSI (Wilder) via RelativeStrengthIndex

    class RSIMeanReversionStrategy(Strategy):  # type: ignore[misc]
        def __init__(self, instrument_id: str, rsi_period: int = 14, overbought: float = 70.0, oversold: float = 30.0, **kwargs: Any) -> None:
            super().__init__()
            self.instrument_id_str = instrument_id
            self.instrument_id = InstrumentId.from_str(instrument_id)
            self.rsi_period = int(max(2, rsi_period))
            self.overbought = float(overbought)
            self.oversold = float(oversold)
            self.qty = int(kwargs.get("qty", 1))
            self.rth_only = bool(kwargs.get("rth_only", False))
            self.eod_flat = bool(kwargs.get("eod_flat", True))
            self.sizing_policy = str(kwargs.get("sizing_policy", "FixedQty"))
            self.sizing_params = dict(kwargs.get("sizing_params", {}))
            # Risk / filters
            self.atr_period = int(kwargs.get("atr_period", 14))
            self.atr_stop_mult = float(kwargs.get("atr_stop_mult", 1.5))
            self.risk_pct = float(kwargs.get("risk_pct", 0.005))
            self.dm_period = int(kwargs.get("dm_period", 14))
            self.di_gap_max = float(kwargs.get("di_gap_max", 10.0))  # avoid strong trends
            self.cooldown_bars = int(kwargs.get("cooldown_bars", 10))
            self.trailing_stop = bool(kwargs.get("trailing_stop", False))

            self.max_notional_pct = float(kwargs.get("max_notional_pct", 0.20))  # cap notional to % of equity

            self._bar_type: BarType | None = None
            self._rsi: RelativeStrengthIndex | None = None
            self._atr: AverageTrueRange | None = None
            self._dm: DirectionalMovement | None = None
            self._prev_rsi: float | None = None
            self._in_position: bool = False
            self._pos_qty: int = 0
            self._entry_px: float | None = None
            self._stop_px: float | None = None
            self._cooldown: int = 0
            self.orders: list[dict[str, Any]] = []
            self.fills: list[dict[str, Any]] = []
            self.equity: list[dict[str, Any]] = []
            self._oid_seq = 0

        def on_start(self) -> None:
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            self._bar_type = BarType(self.instrument_id, spec, AggregationSource.INTERNAL)
            self._rsi = RelativeStrengthIndex(self.rsi_period)
            self._atr = AverageTrueRange(self.atr_period)
            self._dm = DirectionalMovement(self.dm_period)
            self.register_indicator_for_bars(self._bar_type, self._rsi)
            self.register_indicator_for_bars(self._bar_type, self._atr)
            self.register_indicator_for_bars(self._bar_type, self._dm)
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
        def _maybe_eod_flat(self, px: float, ts, mins: int | None) -> None:
            if self.eod_flat and getattr(self, "_in_position", False) and mins is not None and mins == (15 * 60 + 59):
                self._place(OrderSide.SELL, px, ts)


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
            pol = (self.sizing_policy or "FixedQty").lower()
            # equity and cap
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
                pct = float(self.sizing_params.get("pct", 0.01))
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

        def _place(self, side: OrderSide, px: float, ts) -> None:
            from nautilus_trader.model.objects import Quantity
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
            self.orders.append({"ts_utc": ts, "side": "BUY" if side == OrderSide.BUY else "SELL", "qty": qty_int, "price": px, "order_id": oid, "type": "MKT", "time_in_force": "GTC", "reduce_only": reduce_only})

        def on_order_filled(self, event) -> None:  # pragma: no cover
            side = event.order_side
            px = float(event.last_px.as_double()) if hasattr(event, "last_px") else float(event.avg_px.as_double())
            qty = int(event.last_qty) if hasattr(event, "last_qty") else int(event.quantity)
            ts = getattr(event, "ts_event", None)
            if side == OrderSide.BUY:
                self._in_position = True; self._pos_qty = max(0, self._pos_qty + qty)
            else:
                self._pos_qty = max(0, self._pos_qty - qty)
                if self._pos_qty <= 0:
                    self._pos_qty = 0; self._in_position = False
                    self._cooldown = self.cooldown_bars
                    self._entry_px = None; self._stop_px = None
            self.fills.append({"ts_utc": ts, "side": "BUY" if side == OrderSide.BUY else "SELL", "order_id": str(event.client_order_id), "qty": qty, "price": px, "fill_id": str(getattr(event, "trade_id", "unknown")), "slippage": 0.0, "fee": 0.0})

        def on_bar(self, bar) -> None:
            if self._bar_type is None or bar.bar_type != self._bar_type:
                return
            tz_ny = self._get_tz_ny()
            px = float(bar.close.as_double()) if hasattr(bar.close, "as_double") else float(bar.close)
            ts = getattr(bar, "ts_event", None) or getattr(bar, "ts_init", None)
            in_rth, mins = self._in_rth_window(ts, tz_ny, self.rth_only)
            # equity
            try:
                self.equity.append({"ts_utc": ts, "value": float(self._compute_equity_snapshot())})
            except Exception:
                pass
            if not (self._rsi and self._atr and self._dm) or not (self._rsi.initialized and self._atr.initialized and self._dm.initialized):
                return
            # stop-first
            if self._in_position and self._stop_px is not None and px <= float(self._stop_px):
                self._place(OrderSide.SELL, px, ts)
                self._cooldown = self.cooldown_bars
                self._entry_px = None; self._stop_px = None
            # trailing stop
            if self.trailing_stop and self._in_position:
                cand = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                if self._stop_px is None or cand > float(self._stop_px):
                    self._stop_px = cand
            if not in_rth:
                return
            if self._cooldown > 0:
                self._cooldown -= 1
                return
            r = float(self._rsi.value)
            prev = float(self._prev_rsi) if self._prev_rsi is not None else r
            cross_up = prev <= float(self.oversold) and r > float(self.oversold)
            cross_down = prev >= float(self.overbought) and r < float(self.overbought)
            # trend filter: only trade when DM gap is small (non-trending)
            dm_gap_ok = float(abs(self._dm.pos - self._dm.neg)) <= float(self.di_gap_max)
            if (not self._in_position) and cross_up and dm_gap_ok:
                self._entry_px = float(px)
                self._stop_px = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                self._place(OrderSide.BUY, px, ts)
            elif self._in_position and (cross_down or r >= float(self.overbought)):
                self._place(OrderSide.SELL, px, ts)
            self._prev_rsi = r
            self._maybe_eod_flat(px, ts, mins)

except Exception:  # pragma: no cover

    class RSIMeanReversionStrategy:
        def __init__(self, instrument_id: str, rsi_period: int = 14, **_: Any) -> None:
            self.instrument_id = instrument_id
            self.rsi_period = int(rsi_period)

        def __repr__(self) -> str:
            return f"RSIMeanReversionStrategy(period={self.rsi_period}, instrument_id={self.instrument_id})"

