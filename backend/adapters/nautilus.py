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
        # Using a synthetic dataset for validation; ParquetDataAdapter is not used here
        from backend.strategies.strategy_factory import StrategyFactory, StrategyRegistry
        from backend.metrics.standard import StandardMetricsCalculator
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

        engine.add_venue(Venue(venue), OmsType.HEDGING, AccountType.CASH, [Money.from_str("10000 USD")])
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

        # Collect artifacts
        # Collect artifacts from real engine run
        orders: List[Dict[str, Any]] = getattr(strategy, "orders", [])
        fills: List[Dict[str, Any]] = getattr(strategy, "fills", [])
        equity: List[Dict[str, Any]] = getattr(strategy, "equity", [])


        metrics = StandardMetricsCalculator().calculate_metrics(equity=equity, fills=fills)
        return {"orders": orders, "fills": fills, "equity": equity, "metrics": metrics}



