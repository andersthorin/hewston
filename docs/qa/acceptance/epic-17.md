# QA Acceptance — Epic 17 Strategy Expansion and Registry

Scope
- Strategy registry discovery and construction
- New strategies: momentum_v1, rsi_mean_reversion_v1, donchian_breakout_v1
- Canonical artifacts (orders, fills, equity) and metrics availability

Test Matrix
1) Registry
- build(strategy_id=params) constructs from StrategyRegistry
- Unknown strategy_id → 400/clear error from API, safe fallback in CLI

2) Strategy sanity
- momentum_v1 emits at least one order/fill on simple synthetic data
- rsi_mean_reversion_v1 emits BUY/SELL pairs; no negative qty
- donchian_breakout_v1 emits breakout entries and exits

3) Artifacts & metrics
- equity.parquet non-empty, monotonically indexed timestamps
- metrics.json has total_return and max_drawdown

4) Docs/Types
- API spec lists strategy ids and parameter schemas; stories match behavior

Artifacts
- Validate JSON/Parquet shapes in backend/jobs outputs
- Snapshots of API help/strategy catalog (if exposed)

