# Epic 17 Addendum — Architect Review

Key Additions
- StrategyParams schemas (pydantic) validated in StrategyFactory before instantiation.
- Consistent RTH/timezone handling; strategies honor rth_only and eod_flat.
- Subscription discipline: subscribe only to required instrument(s); align with quotes data.
- Safety switches: per-strategy position size caps.

Notes
- If a strategy needs bars, define derivation from quotes (mid → bars) or restrict to quotes-only variants.
- Provide default parameter sets suitable for equities/XNAS.

References
- ADR-005 Metrics & Guardrails Baseline
- Epic 19 sizing hooks

