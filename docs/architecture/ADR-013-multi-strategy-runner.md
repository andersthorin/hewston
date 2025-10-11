# ADR-013 — Multi-Strategy Runner (Epic 20)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 20; Stories: 20.1–20.5

## Context
We need to run multiple strategies against the same dataset/instrument window as a single composite run for plan-scale evaluation.

## Decision
- Extend job args and manifest schema to support `strategies: [{strategy_id, params}]` alongside a default single-strategy mode.
- Persist artifacts per strategy (namespaced) and aggregate summary metrics at the run root (e.g., best/worst total_return, weighted combos TBD).
- Maintain a single run_id and directory root, with per-strategy sub-artifacts (equity.parquet, fills.parquet, etc.) and a combined metrics.json.

## Consequences
- Enables fair comparison of strategies on identical data windows.
- Slightly larger storage footprint; acceptable for evaluation runs.

## Implementation Notes
- Backward compat: if `strategies` absent, treat legacy fields as the single entry.
- Update API surface for /backtests/{id}/complete to include per-strategy metrics.

## Testing
- Integration: multi-strategy job writes per-strategy artifacts and combined metrics; manifest validates.

## Alternatives
- Separate run_ids for each strategy (rejected; complicates UX and Agentic aggregation).

## References
- docs/prd/epic-20-nautilus-multi-strategy-runner.md

