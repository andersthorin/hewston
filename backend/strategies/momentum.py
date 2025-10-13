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
    from nautilus_trader.indicators.atr import AverageTrueRange  # type: ignore
    from nautilus_trader.indicators.dm import DirectionalMovement  # type: ignore
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
            self.eod_flat = bool(kwargs.get("eod_flat", True))
            self.sizing_policy = str(kwargs.get("sizing_policy", "FixedQty"))
            self.sizing_params = dict(kwargs.get("sizing_params", {}))
            # Risk / filters
            self.atr_period = int(kwargs.get("atr_period", 14))
            self.atr_stop_mult = float(kwargs.get("atr_stop_mult", 1.5))
            self.risk_pct = float(kwargs.get("risk_pct", 0.005))
            self.dm_period = int(kwargs.get("dm_period", 14))
            self.di_gap_min = float(kwargs.get("di_gap_min", 5.0))
            self.band_k = float(kwargs.get("band_k", 0.25))
            self.sma_slope_min = float(kwargs.get("sma_slope_min", 0.0))
            self.cooldown_bars = int(kwargs.get("cooldown_bars", 10))
            self.trailing_stop = bool(kwargs.get("trailing_stop", False))
            self.max_notional_pct = float(kwargs.get("max_notional_pct", 0.20))  # cap notional to % of equity

            # Optional time-of-day entry window in NY minutes since midnight (inclusive)
            # Example: entry_start_min=600 (10:00), entry_end_min=930 (15:30)
            try:
                self.entry_start_min = int(kwargs.get("entry_start_min")) if kwargs.get("entry_start_min") is not None else None
            except Exception:
                self.entry_start_min = None
            try:
                self.entry_end_min = int(kwargs.get("entry_end_min")) if kwargs.get("entry_end_min") is not None else None
            except Exception:
                self.entry_end_min = None


            self._bar_type: BarType | None = None
            self._sma: SimpleMovingAverage | None = None
            self._atr: AverageTrueRange | None = None
            self._dm: DirectionalMovement | None = None
            self._prev_sma: float | None = None
            self._cooldown: int = 0
            self._in_position: bool = False
            self._pos_qty: int = 0
            self._entry_px: float | None = None
            self._stop_px: float | None = None
            self.orders: list[dict[str, Any]] = []
            self.fills: list[dict[str, Any]] = []
            self.equity: list[dict[str, Any]] = []
            self._oid_seq = 0

        def on_start(self) -> None:
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            self._bar_type = BarType(self.instrument_id, spec, AggregationSource.INTERNAL)
            self._sma = SimpleMovingAverage(self.window)
            self._atr = AverageTrueRange(self.atr_period)
            self._dm = DirectionalMovement(self.dm_period)
            self.register_indicator_for_bars(self._bar_type, self._sma)
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
        def _filters_ok(self) -> bool:
            if not (self._sma and self._atr and self._dm):
                return False
            if not (self._sma.initialized and self._atr.initialized and self._dm.initialized):
                return False
            try:
                s = float(self._sma.value); ps = float(self._prev_sma) if self._prev_sma is not None else s
                slope = s - ps
                if slope < float(self.sma_slope_min):
                    return False
            except Exception:
                return False
            try:
                gap = float(self._dm.pos - self._dm.neg)
                if gap < float(self.di_gap_min):
                    return False
            except Exception:
                return False
            return True


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
            """Compute order size with notional cap and all policies supported."""
            try:
                pol = (self.sizing_policy or "FixedQty").lower()
            except Exception:
                pol = "fixedqty"

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

        def _place(self, side: OrderSide, px: float, ts) -> None:
            from nautilus_trader.model.objects import Quantity

            # For exits, ensure reduce-only and use current position size to avoid shorting
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
                # If reduce_only param unsupported, fall back to regular market; qty is position-sized on exits
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
            # Local minutes in NY (independent of rth_only)
            mins_local = None
            try:
                if tz_ny is not None and ts is not None:
                    from datetime import datetime, timezone
                    dt = None
                    if isinstance(ts, (int, float)):
                        # ts is epoch nanoseconds
                        dt = datetime.fromtimestamp(float(ts) / 1e9, tz=timezone.utc)
                    elif hasattr(ts, "to_pydatetime"):
                        dt = ts.to_pydatetime()
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    elif hasattr(ts, "astimezone"):
                        dt = ts
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    if dt is not None:
                        local = dt.astimezone(tz_ny)
                        mins_local = local.hour * 60 + local.minute
            except Exception:
                mins_local = None
            # equity track
            try:
                self.equity.append({"ts_utc": ts, "value": float(self._compute_equity_snapshot())})
            except Exception:
                pass
            # hard stop check
            if self._in_position and self._stop_px is not None and px <= float(self._stop_px):
                self._place(OrderSide.SELL, px, ts)
                self._cooldown = self.cooldown_bars
                self._entry_px = None; self._stop_px = None
            # trailing update
            if self.trailing_stop and self._in_position and self._atr and self._atr.initialized:
                cand = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                if self._stop_px is None or cand > float(self._stop_px):
                    self._stop_px = cand
            if not in_rth:
                return
            if self._cooldown > 0:
                self._cooldown -= 1
                return

            # Optional time-of-day entry window (NY minutes since midnight)
            allowed_entry_now = True
            if (getattr(self, "entry_start_min", None) is not None) and (getattr(self, "entry_end_min", None) is not None):
                try:
                    ms = int(mins_local) if mins_local is not None else None
                    if ms is None or not (int(self.entry_start_min) <= ms <= int(self.entry_end_min)):
                        allowed_entry_now = False
                except Exception:
                    # Fail-open if parsing fails
                    allowed_entry_now = True
            # Debug: log a few samples of entry window evaluation
            try:
                if not hasattr(self, "_tod_dbg"): self._tod_dbg = {"ok": 0, "no": 0}
                if getattr(self, "entry_start_min", None) is not None and getattr(self, "entry_end_min", None) is not None:
                    if allowed_entry_now and self._tod_dbg["ok"] < 5:
                        self._tod_dbg["ok"] += 1
                        self._log.info(f"[TOD] allowed at ts={ts}, mins_local={mins_local}")
                    elif (not allowed_entry_now) and self._tod_dbg["no"] < 5:
                        self._tod_dbg["no"] += 1
                        self._log.info(f"[TOD] blocked at ts={ts}, mins_local={mins_local}")
            except Exception:
                pass

            # signals with filters
            if self._sma and self._atr and self._dm and self._sma.initialized and self._atr.initialized and self._dm.initialized:
                m = float(self._sma.value)
                band_ok = (px - m) >= float(self.band_k) * float(self._atr.value)
                slope_ok = (float(m) - float(self._prev_sma if self._prev_sma is not None else m)) >= float(self.sma_slope_min)
                gap_ok = (float(self._dm.pos - self._dm.neg) >= float(self.di_gap_min))
                if (not self._in_position) and band_ok and slope_ok and gap_ok and allowed_entry_now:
                    self._entry_px = float(px)
                    self._stop_px = float(px) - float(self.atr_stop_mult) * float(self._atr.value)
                    self._place(OrderSide.BUY, px, ts)
                elif self._in_position and px < m:
                    self._place(OrderSide.SELL, px, ts)
                self._prev_sma = m
            # EOD flatten
            self._maybe_eod_flat(px, ts, mins_local)


except Exception:  # pragma: no cover - placeholder when Nautilus not installed

    class MomentumStrategy:
        def __init__(self, instrument_id: str, window: int = 20, **_: Any) -> None:
            self.instrument_id = instrument_id
            self.window = int(window)

        def __repr__(self) -> str:  # debug-only
            return f"MomentumStrategy(window={self.window}, instrument_id={self.instrument_id})"

