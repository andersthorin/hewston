# ADR-006 — Cost Model Calibration

Status
- Proposed

Context
- Backtests on quotes must include plausible trading costs to avoid inflated metrics. We need a simple, configurable cost model to start.

Decision
- Use a baseline cost model composed of:
  - Slippage: half-spread on entry and exit (mid→fill at ±0.5×spread), configurable multiplier.
  - Fees: flat per-trade fee or basis points of notional (venue-configurable), default conservative.

Rationale
- Half-spread is a standard first approximation with quotes data.
- Separating slippage and fees allows independent tuning.

Calibration
- Record average spread proxies per symbol/day if available; otherwise use global defaults.
- Provide a calibration harness (Story 19.5) to sweep multipliers and compare sensitivity.

Observability
- Persist cost_model.json per run with parameters used (slippage_multiplier, fee_bps, fee_fixed, source_of_spread).
- Metrics.json must include both raw and cost-adjusted values.

Consequences
- Rankings reflect tradability; overly high-turnover strategies will be penalized.

Default Parameters (initial)
- slippage_multiplier: 1.0 (half-spread per entry/exit)
- fee_bps: 1.0 (per-trade notional basis points)
- fee_fixed: 0.0 (optional, default off)
- source_of_spread: observed if available; otherwise global default

Usage
- Persist cost_model.json with these parameters per run; document any overrides in the manifest.


Evolution
- Later: depth-aware or volatility-scaled slippage; venue- and time-of-day–dependent fees.

Links
- ADR-005 Metrics and Guardrails Baseline
- Epic 19 PRD/Plan

