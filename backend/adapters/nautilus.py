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
        from backend.adapters.nautilus_data import ParquetDataAdapter, BarsWindow
        from backend.strategies.strategy_factory import StrategyFactory, StrategyRegistry
        from backend.metrics.standard import StandardMetricsCalculator
        try:
            from nautilus_trader.backtest.engine import BacktestEngine  # type: ignore
            from nautilus_trader.model.identifiers import Venue  # type: ignore
            from nautilus_trader.model.enums import OmsType, AccountType  # type: ignore
            from nautilus_trader.model.objects import Money  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ImportError("nautilus-trader is required for real engine execution") from e

        adapter = ParquetDataAdapter()
        window = BarsWindow(from_date=from_date, to_date=to_date)
        bars_df = adapter.load_bars(dataset_id=dataset_id, window=window)
        instrument_id = adapter.dataset_to_instrument_id(dataset_id)
        bars = adapter.convert_to_nautilus(bars_df=bars_df, instrument_id=instrument_id)
        data_engine = adapter.create_data_engine(bars)

        # Build strategy
        params_with_instrument = dict(params)
        params_with_instrument.setdefault("instrument_id", instrument_id)
        params_with_instrument.setdefault("qty", 1)
        strategy = StrategyFactory(StrategyRegistry()).build(strategy_id, params_with_instrument)

        # Engine wiring
        engine = BacktestEngine(data_engine=data_engine, strategies=[strategy], seed=seed)  # type: ignore[arg-type]
        engine.add_venue(Venue("XNAS"), OmsType.HEDGING, AccountType.CASH, [Money.from_str("10000 USD")])
        engine.run()

        # Collect artifacts
        orders: List[Dict[str, Any]] = getattr(strategy, "orders", [])
        fills: List[Dict[str, Any]] = getattr(strategy, "fills", [])
        equity: List[Dict[str, Any]] = getattr(strategy, "equity", [])

        metrics = StandardMetricsCalculator().calculate_metrics(equity=equity, fills=fills)
        return {"orders": orders, "fills": fills, "equity": equity, "metrics": metrics}

