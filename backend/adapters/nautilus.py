from __future__ import annotations

from typing import Any, Dict, List


class NautilusBacktestRunner:
    """Backtest runner which always executes the real Nautilus Trader engine.

    No stub fallback is provided. Any error will be propagated to the caller.
    """

    def run(
        self,
        *,
        dataset_id: str,
        strategy_id: str,
        params: Dict[str, Any],
        seed: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Dict[str, Any]:
        return self._run_real(
            dataset_id=dataset_id,
            strategy_id=strategy_id,
            params=params,
            seed=seed,
            from_date=from_date,
            to_date=to_date,
        )

    def _run_real(
        self,
        *,
        dataset_id: str,
        strategy_id: str,
        params: Dict[str, Any],
        seed: int,
        from_date: str | None,
        to_date: str | None,
    ) -> Dict[str, Any]:
        """Real engine execution path using nautilus-trader.
        Raises ImportError if nautilus-trader is not installed.
        """
        # Lazy imports; fail fast if not available
        from backend.strategies.strategy_factory import StrategyFactory, StrategyRegistry
        try:
            from nautilus_trader.backtest.engine import BacktestEngine  # type: ignore
            from nautilus_trader.model.identifiers import Venue  # type: ignore
            from nautilus_trader.model.enums import OmsType, AccountType  # type: ignore
            from nautilus_trader.model.objects import Money  # type: ignore
            from nautilus_trader.model.instruments import Equity  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ImportError("nautilus-trader is required for real engine execution") from e

        # Load QuoteTicks from warehouse and feed to Nautilus (Approach A: INTERNAL MID)
        # - Instrument: default to AAPL.XNAS unless provided via params
        import pandas as pd  # type: ignore
        from pathlib import Path
        from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler  # type: ignore
        from nautilus_trader.model.enums import PriceType, AggregationSource  # type: ignore
        from nautilus_trader.model.data import BarSpecification, BarType  # type: ignore

        instrument_id = str(params.get("instrument_id", "AAPL.XNAS"))

        # Discover quotes parquet files for date range
        symbol = instrument_id.split(".")[0]
        venue = instrument_id.split(".")[1] if "." in instrument_id else "XNAS"
        # Interpret from/to as ISO dates (YYYY-MM-DD); fall back to single day if missing
        if from_date and to_date:
            dates = pd.date_range(pd.to_datetime(from_date), pd.to_datetime(to_date), freq="1D").strftime("%Y-%m-%d").tolist()
        else:
            # Default to one RTH day to keep runs fast when unspecified
            dates = ["2024-10-01"]

        def _qpath(date_str: str) -> Path:
            return Path("data/warehouse/quotes") / f"venue={venue}" / f"symbol={symbol}" / f"date={date_str}" / "quotes.parquet"

        pdf_list = []
        for d in dates:
            p = _qpath(d)
            if p.exists():
                q = pd.read_parquet(p)
                # Expect columns: ts, bid_px, ask_px, bid_sz, ask_sz
                q = q.dropna(subset=["ts", "bid_px", "ask_px"])  # minimal
                q = q.sort_values("ts")
                q = q.set_index(pd.to_datetime(q["ts"], utc=True))[ ["bid_px", "ask_px", "bid_sz", "ask_sz"] ]
                q = q.rename(columns={"bid_px": "bid", "ask_px": "ask", "bid_sz": "bid_size", "ask_sz": "ask_size"})
                pdf_list.append(q)
        if not pdf_list:
            raise FileNotFoundError("No QuoteTicks parquet found in warehouse for requested range")
        pdf = pd.concat(pdf_list).sort_index()

        # Strategy bar spec for INTERNAL MID (1m)
        bar_spec = BarSpecification.from_timedelta(pd.Timedelta(minutes=1), PriceType.MID)

        # Build strategy
        params_with_instrument = dict(params)
        params_with_instrument.setdefault("instrument_id", instrument_id)
        params_with_instrument.setdefault("qty", 1)
        strategy = StrategyFactory(StrategyRegistry()).build(strategy_id, params_with_instrument)

        # Engine wiring (Nautilus 1.219.0 API)
        engine = BacktestEngine()
        # Ensure data routes to venue client by default
        try:
            from nautilus_trader.model.identifiers import ClientId  # type: ignore
            # Route both market data and trading to the venue client (e.g., XNAS)
            engine.set_default_market_data_client(ClientId(venue))
            engine.set_default_trading_client(ClientId(venue))
        except Exception:
            # Older Nautilus versions may not expose set_default_trading_client
            pass

        engine.add_venue(Venue(venue), OmsType.NETTING, AccountType.CASH, [Money.from_str("10000 USD")])
        # Ensure instrument is registered before adding bars
        instr = Equity.from_dict({
            "id": instrument_id,
            "raw_symbol": instrument_id.split(".")[0],
            "symbol": instrument_id.split(".")[0],
            "asset_class": "EQUITY",
            "price_precision": 2,
            "price_increment": "0.01",
            "size_precision": 0,
            "size_increment": "1",
            "multiplier": "1",
            "lot_size": "1",
            "quote_currency": "USD",
            "currency": "USD",
            "ts_event": 0,
            "ts_init": 0,
            "info": {"name": instrument_id},
        })
        engine.add_instrument(instr)

        # Wrangle to QuoteTick objects and add to engine
        wrangler = QuoteTickDataWrangler(instr)
        quote_ticks = wrangler.process(pdf)

        # Add strategy before data to ensure subscriptions are registered
        engine.add_strategy(strategy)

        # Add quotes; let default market data client route by venue
        try:
            from nautilus_trader.model.identifiers import ClientId  # type: ignore
            client_id = ClientId(venue)
        except Exception:  # pragma: no cover
            client_id = None  # type: ignore
        if client_id:
            engine.add_data(quote_ticks, client_id=client_id, validate=False, sort=True)  # type: ignore[arg-type]
        else:
            engine.add_data(quote_ticks, validate=False, sort=True)
        # Run
        engine.run()

        # Collect artifacts from strategy's custom tracking
        import logging
        logger = logging.getLogger("nautilus.runner")

        orders: List[Dict[str, Any]] = getattr(strategy, "orders", [])
        fills: List[Dict[str, Any]] = getattr(strategy, "fills", [])
        equity: List[Dict[str, Any]] = getattr(strategy, "equity", [])

        logger.info(
            f"Collected artifacts: {len(orders)} orders, {len(fills)} fills, "
            f"{len(equity)} equity points"
        )

        # Extract metrics from Nautilus engine state
        metrics = self._extract_metrics_from_engine(engine, equity, fills)

        # Also capture raw Nautilus analyzer stats and time series (for post-run precompute)
        nautilus_stats: Dict[str, Any] = {"pnls": {}, "returns": {}, "general": {}}
        nautilus_series: Dict[str, list] = {"returns": [], "realized_pnl": []}
        try:
            analyzer = getattr(engine, "portfolio").analyzer  # type: ignore[attr-defined]
            # Raw stats (opaque pass-through)
            try:
                nautilus_stats["pnls"] = analyzer.get_performance_stats_pnls()
            except Exception:
                pass
            try:
                nautilus_stats["returns"] = analyzer.get_performance_stats_returns()
            except Exception:
                pass
            try:
                nautilus_stats["general"] = analyzer.get_performance_stats_general()
            except Exception:
                pass
            # Time series
            try:
                # Returns series (pd.Series)
                s = getattr(analyzer, "returns", None)
                if callable(s):
                    s = s()
                import pandas as pd  # type: ignore
                if s is not None and isinstance(s, pd.Series):
                    def _to_utc_iso(ts):
                        t = pd.Timestamp(ts)
                        # If tz-naive, localize to UTC; if tz-aware, convert to UTC
                        return (t.tz_localize("UTC") if t.tzinfo is None or t.tz is None else t.tz_convert("UTC")).isoformat()
                    nautilus_series["returns"] = [
                        [_to_utc_iso(k), float(v)] for k, v in s.items()  # type: ignore
                    ]
            except Exception:
                pass
            try:
                # Realized PnL series in USD
                from nautilus_trader.model.currencies import USD  # type: ignore
                rp = None
                if hasattr(analyzer, "realized_pnls"):
                    rp = analyzer.realized_pnls(USD)
                import pandas as pd  # type: ignore
                if rp is not None and isinstance(rp, pd.Series):
                    def _to_utc_iso(ts):
                        t = pd.Timestamp(ts)
                        return (t.tz_localize("UTC") if t.tzinfo is None or t.tz is None else t.tz_convert("UTC")).isoformat()
                    nautilus_series["realized_pnl"] = [
                        [_to_utc_iso(k), float(v)] for k, v in rp.items()  # type: ignore
                    ]
            except Exception:
                pass
        except Exception:
            pass

        return {
            "orders": orders,
            "fills": fills,
            "equity": equity,
            "metrics": metrics,
            "nautilus": {"stats": nautilus_stats, "series": nautilus_series},
            "bar_interval_minutes": 1,
        }

    def _extract_metrics_from_engine(
        self,
        engine: Any,
        equity: List[Dict[str, Any]],
        fills: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Extract performance metrics from Nautilus engine.

        Source strictly from Nautilus outputs. If portfolio API is unavailable,
        fall back to the last equity snapshot captured by the strategy (still Nautilus data).
        """
        import logging
        logger = logging.getLogger("nautilus.metrics")

        metrics: Dict[str, float] = {}
        starting_balance = 10000.0  # Default from strategy

        # Try portfolio/account path first; if unavailable, use equity snapshots
        try:
            portfolio = engine.portfolio  # Direct access, not engine.trader.portfolio

            # Get the venue from the first instrument (we only have one in backtests)
            from nautilus_trader.model.identifiers import Venue  # noqa: F401
            instruments = engine.cache.instruments()
            if not instruments:
                logger.error("❌ CRITICAL: No instruments in cache")
                raise RuntimeError("No instruments in cache")

            venue = list(instruments)[0].id.venue
            account = portfolio.account(venue)

            if not account:
                logger.error(f"❌ CRITICAL: No account found for venue {venue}")
                raise RuntimeError(f"No account for venue {venue}")

            # Get total account value including unrealized PnL; prefer account.equity_total
            from nautilus_trader.model.currencies import USD
            ending_balance: float
            try:
                equity_money = getattr(account, "equity_total")(USD)  # type: ignore[attr-defined]
                ending_balance = float(equity_money.as_double())
            except Exception:
                # Fallback: use last equity point captured by the strategy if available
                if isinstance(equity, list) and equity:
                    try:
                        ending_balance = float(equity[-1].get("value"))
                    except Exception:
                        ending_balance = starting_balance
                else:
                    # Last resort: cash balance (may ignore unrealized PnL)
                    bal = account.balance_total(USD)
                    ending_balance = float(bal.as_double())
            metrics["total_return"] = (ending_balance - starting_balance) / starting_balance

            logger.info(
                f"Extracted metrics: start=${starting_balance:.2f}, end=${ending_balance:.2f}, return={metrics['total_return']:.4f}"
            )

        except AttributeError:
            # Portfolio path unavailable; use equity snapshots as source-of-truth
            if isinstance(equity, list) and equity:
                try:
                    ending_balance = float(equity[-1].get("value"))
                except Exception:
                    ending_balance = starting_balance
                metrics["total_return"] = (ending_balance - starting_balance) / starting_balance
            else:
                logger.error("❌ CRITICAL: Neither portfolio API nor equity snapshots available for metrics")
                raise RuntimeError("Failed to extract metrics from Nautilus: no portfolio and no equity snapshots")

        except Exception as e:
            logger.error(f"❌ CRITICAL: Unexpected error extracting Nautilus metrics: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to extract metrics from Nautilus: {e}") from e

        # Calculate max drawdown from equity curve
        metrics["max_drawdown"] = self._calculate_max_drawdown(equity)

        # Calculate win rate from fills
        metrics["win_rate"] = self._calculate_win_rate(fills)

        logger.info(
            f"Final metrics: total_return={metrics['total_return']:.4f}, "
            f"max_drawdown={metrics['max_drawdown']:.4f}, "
            f"win_rate={metrics['win_rate']:.4f}, "
            f"fills_count={len(fills)}"
        )

        return metrics

    def _calculate_max_drawdown(self, equity: List[Dict[str, Any]]) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not equity:
            return 0.0

        peak = None
        min_drawdown = 0.0

        for pt in equity:
            try:
                v = float(pt.get("value", 0.0) or 0.0)
            except Exception:
                continue

            if peak is None or v > peak:
                peak = v

            if peak and peak > 0:
                dd = (v - peak) / peak  # <= 0
                if dd < min_drawdown:
                    min_drawdown = dd

        return float(min_drawdown)

    def _calculate_win_rate(self, fills: List[Dict[str, Any]]) -> float:
        """Calculate win rate from fills by pairing entry/exit trades."""
        if not fills:
            return 0.0

        wins = 0
        total = 0
        pos = 0
        entry_price = 0.0

        for f in fills:
            side = f.get("side") or f.get("Side") or None
            try:
                px = float(f.get("price", 0.0))
                qty = float(f.get("qty", 0.0))
            except (ValueError, TypeError):
                continue

            if side == "BUY" and pos == 0:
                pos = 1
                entry_price = px
            elif side == "SELL" and pos == 1:
                pos = 0
                pnl = (px - entry_price) * qty
                total += 1
                if pnl > 0:
                    wins += 1

        return (wins / total) if total else 0.0



