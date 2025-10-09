# Epic 19 — Calibration Appendix

Purpose
- Provide initial defaults and a process to tune guardrails and cost model parameters using the calibration harness.

Defaults (initial)
- Coverage: ≥ 90% NYSE trading days
- Min trades: ≥ 30 total or ≥ 1/day
- Max DD stop: 25%
- Turnover cap: 10–15× per month equivalent
- Cost model: slippage_multiplier=1.0 (half-spread), fee_bps=1.0, fee_fixed=0.0

Process
1) Select a representative sample window and symbols (at least two market regimes if possible)
2) Use Story 19.5 to sweep slippage_multiplier ∈ {0.5, 1.0, 1.5}, fee_bps ∈ {0.5, 1.0, 2.0}
3) Compare cost-adjusted metrics vs raw; inspect turnover sensitivity
4) Adjust thresholds upward if too many false positives (unrealistic winners); downward if too strict
5) Record chosen parameters in ADR-006 and defaults in config; persist calibration report

Outputs
- calibration_report.md with tables/plots and chosen parameter set
- Updated thresholds in orchestrator config and docs

