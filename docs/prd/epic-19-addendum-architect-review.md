# Epic 19 Addendum — Architect Review

Key Additions
- Volatility estimation: EWMA(λ=0.94) on mid-returns by default; optional rolling std(window=20d). Persist method + params in metrics.json.
- Cost model baseline: half-spread slippage + fee model (see ADR-006). Persist cost_model.json.
- Dynamic guardrails: thresholds scale with window length (trades/day, turnover tightening). Add stability indicator (e.g., equity kink/drawdown clustering).
- Calibration harness: scripts/tests to sweep cost/threshold multipliers and observe sensitivity.

References
- ADR-005 Metrics & Guardrails Baseline
- ADR-006 Cost Model Calibration

