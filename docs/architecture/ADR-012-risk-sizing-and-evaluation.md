# ADR-012 — Risk Sizing and Evaluation Policies (Epic 19)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 19; Stories: 19.1–19.5

## Context
We need simple, configurable sizing and risk constraints to support strategy evaluation and plan simulation without broker coupling.

## Decision
- Introduce pluggable sizing policies (FixedQty, PercentOfEquity, VolTarget) wired at strategy construction via params.
- Enforce risk constraints at runner/strategy boundary: max position, max daily risk, trading hours filters (RTH-only), EOD flatten.
- Surface evaluation metrics consistently: total_return, max_drawdown, win_rate, Sharpe (if available), end_position_qty.
- Record policy selections in run manifest.

## Consequences
- Comparable runs across strategies using the same sizing policy.
- Clear knobs for Agentic plan generation and guardrails.

## Implementation Notes
- StrategyFactory maps ‘sizing_policy’ and related params into strategy kwargs.
- Runner validates outputs and surfaces standard metrics; fallbacks allowed when Nautilus portfolio API is limited.

## Testing
- Unit tests per policy: order sizes and constraint enforcement.
- Integration: metrics exist and are consistent across policies.

## Alternatives
- Sizing inside the runner only (rejected; strategy-local signals need access to quantity intent).

## References
- docs/prd/epic-19-risk-sizing-and-evaluation.md
- docs/architecture/nautilus-integration-architecture.md

