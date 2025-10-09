# Epic 17 — Strategy Expansion and Registry (Equities/XNAS)

Goal
- Expand beyond SMA with additional, robust strategies suitable for equities backtests. Provide schemas/defaults and register them for agentic selection.

Why (Value)
- Diversifies the strategic toolkit and enables the Agentic Mode to explore multiple approaches on each symbol.

Scope (In)
- New strategies (single-instrument each):
  - Momentum (rate-of-change or linear-regression slope)
  - Mean Reversion (RSI-based)
  - Breakout/Trend (Donchian or price channel)
- Parameter schemas & defaults:
  - JSON-schema or pydantic models for each strategy (periods, thresholds, trade_size policy)
- StrategyRegistry additions:
  - Register new strategy_ids and import paths
- Tests and fixtures:
  - Smoke tests: each strategy runs on a small sample and emits orders/fills
  - Golden metrics snapshots (tolerances) to detect regressions

Scope (Out)
- Cross-instrument strategies (defer)
- Asset classes other than equities

Design
- Strategy instances are created per symbol with their own instrument_id
- Sizing will defer to Epic 19 (vol-normalized or fixed-size)
- Enable rth_only/eod_flat toggles where applicable

Acceptance Criteria
- Strategies instantiable via StrategyFactory with defaults
- Strategies produce sensible trades on demo datasets
- Registered for agentic selection; surfaced in plan preview

Milestones
1) Implement Momentum + RSI MR + Breakout strategies
2) Parameter schemas/defaults + registry updates
3) Unit tests with golden metrics
4) Docs: brief usage examples in docs/architecture/strategy-notes.md

