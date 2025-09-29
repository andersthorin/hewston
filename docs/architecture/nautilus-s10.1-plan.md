# S10.1 Implementation Plan — Core Nautilus Engine Integration (MVP)

Epic: E10 — Nautilus Trader Full Implementation  
Scope: Replace stub with real Nautilus backtesting; SMA strategy; PnL + win rate metrics

## Objectives
- Integrate Nautilus BacktestEngine using 1m OHLCV bars
- Implement StrategyRegistry/Factory (SMA only in MVP)
- Produce artifacts in existing format (orders.parquet, fills.parquet, equity.parquet, metrics.json)
- Compute MVP metrics (total_return, win_rate) and preserve JSON format
- Keep feature flag to fallback to stub

## Deliverables
1) New NautilusBacktestRunner implementation behind BacktestRunnerPort
2) ParquetDataAdapter for bar loading/filtering and conversion
3) SMA strategy implemented in Nautilus style and registered
4) Artifact formatting functions (Nautilus results → parquet/json)
5) MVP metrics calculation from results
6) Integration tests + baseline performance check

## Technical Steps

1. Data Adapter
- Implement `ParquetDataAdapter.load_bars(dataset_id, from_date, to_date) -> pl.DataFrame`
  - Resolve parquet path from catalog
  - Read columns: t|ts, o,h,l,c,v
  - Filter inclusive window if provided
  - Validate monotonic timestamps; drop NaNs in OHLC
- Implement `convert_to_nautilus(bars_df) -> list[Bar]`
  - Rename to pandas columns: timestamp/open/high/low/close/volume (tz-aware UTC index)
  - Use Nautilus `BarDataWrangler` to produce Bar list
- Implement `create_data_engine(bars) -> DataEngine`

2. Instrument & BarType
- Map `dataset_id -> instrument_id = SYMBOL.XNAS` (uppercase)
- Construct Instrument and 1-minute BarType

3. Strategy Framework (MVP)
- Create `StrategyRegistry` & `StrategyFactory`
- Implement `SMAStrategy`:
  - Parameters: fast:int, slow:int (fast < slow)
  - Signals: cross-over generate entries/exits long-only
  - No pyramiding; position in {0,1}
- Register `sma_crossover`

4. Backtest Runner
- Replace `NautilusBacktestRunner.run(...)` internals:
  - Load & convert bars → DataEngine
  - Build strategy via factory
  - Configure & run BacktestEngine
  - Collect orders, fills, equity, native performance
  - Compute metrics (total_return, win_rate)
  - Format artifacts to existing schemas
- Respect `HEWSTON_USE_NAUTILUS_STUB` feature flag for fallback

5. Slippage & Fees (MVP)
- Params: `slippage_bps=1`, `fee_bps=1` (configurable)
- Adjust fill prices and compute fee on notional

6. Artifacts Formatting (MVP)
- Orders parquet: ts_utc, order_id, side, type=MKT, tif=IOC, qty, price
- Fills parquet: ts_utc, order_id, fill_id, side, qty, price (post-slippage), fee
- Equity parquet: ts_utc, value
- Metrics JSON: total_return, win_rate

7. Metrics Calculation (MVP)
- total_return = (final_equity - initial_equity) / initial_equity
- win_rate from trade pairing (entry 0→1, exit 1→0), PnL>0 counts as win

8. Tests
- Unit: adapter conversion; SMA signals; metrics functions (PnL, win_rate)
- Integration: end-to-end backtest generates artifacts with expected schema
- Performance: 1-year AAPL run ≤ 30s on M1 dev box (best-effort), minimal logs

## Acceptance Checks
- BacktestRunnerPort signature unchanged; `make backtest` works
- Artifacts generated exactly as before (schemas match)
- Metrics.json includes total_return and win_rate keys
- Feature flag toggles between stub and real engine
- Test suite passes; integration test verifies real Nautilus path

## Performance Checklist (M1)
- Use Polars lazy read or scan; avoid pandas until wrangler step
- Limit logging in hot paths; prefer INFO for boundaries only
- Ensure UTC tz handling avoids costly conversions in loops
- Validate no large Python loops over bars; use vector ops where possible pre-wrangler

## Rollback Plan
- Set `HEWSTON_USE_NAUTILUS_STUB=true` to revert to stub without code changes

## Work Breakdown (suggested tasks)
- A) Adapter + Instrument/BarType (4–6h)
- B) SMA strategy + registry/factory (4–6h)
- C) Runner integration + artifacts formatting (6–8h)
- D) Metrics + tests (4–6h)
- E) Perf pass + polish (2–4h)

## Risks
- Nautilus wheels on Apple Silicon — prefer pinned version with wheels
- Data timezone drift — enforce UTC and validation
- Performance regressions — keep simple, avoid extra copies

## References
- Architecture: docs/architecture/nautilus-integration-architecture.md
- Epic/Stories: docs/prd/epic-10-nautilus-trader-full-implementation.md, docs/stories/10.1.story.md
- Nautilus Docs: Backtest low-level, Persistence (BarDataWrangler)

