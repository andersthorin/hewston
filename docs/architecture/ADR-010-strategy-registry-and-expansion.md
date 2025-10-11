# ADR-010 — Strategy Registry and Expansion (Epic 17)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 17; Stories: 17.1–17.5
References: StrategyFactory/StrategyRegistry, Nautilus integration

## Context
We want to expand the built-in strategy set (beyond SMA) and standardize how strategies are discovered and instantiated. This supports Agentic plans selecting strategies by id and passing parameters in a stable schema.

## Decision
- Centralize construction behind StrategyFactory + StrategyRegistry mapping `strategy_id -> builder`.
- Register initial set:
  - sma_crossover (existing)
  - momentum_v1
  - rsi_mean_reversion_v1
  - donchian_breakout_v1
- Normalize parameter schema across strategies (instrument_id, fast/slow or window params, qty, eod_flat, rth_only). Provide defaults in registry.
- Ensure strategies emit canonical artifacts (orders/fills/equity) consumed by the runner.

## Consequences
- Consistent UX across strategies; Agentic plans stay simple and portable.
- Easier testing and mocking since construction is unified.

## Implementation Notes
- backend/strategies/strategy_factory.py: add registry entries and input normalization.
- Implement new strategy classes under backend/strategies/ (or adapter-backed wrappers) with identical artifact surfaces.
- Document strategy ids and parameters in API reference.

## Testing
- Unit tests per strategy: signals sanity (happy-path) and artifact production.
- Integration: backtest run returns metrics and non-empty equity for supported datasets.

## Alternatives
- Dynamic import by module path (rejected for now; registry gives clearer control and docs).

## References
- docs/prd/epic-17-strategy-expansion-and-registry.md
- docs/architecture/nautilus-integration-architecture.md

