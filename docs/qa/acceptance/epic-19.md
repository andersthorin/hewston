# QA Acceptance — Epic 19 Risk, Sizing, and Evaluation

Scope
- Sizing policies, risk constraints, metrics/costs, guardrails integration

Test Matrix
1) Sizing
- Vol-normalized: stable target risk with varying volatility inputs
- Fixed-size fallback triggers when vol unavailable; flag present in manifest

2) Constraints
- Per-symbol exposure cap applied
- Account-level cap applied
- Max DD stop halts run and records reason
- Daily trade cap enforced

3) Metrics & costs
- metrics.json contains raw and cost-adjusted metrics; methods documented
- Cost model parameters persisted in cost_model.json

4) Guardrails
- coverage_ok, min_trades_ok, turnover_ok, max_dd_ok, no_nans — pass/fail cases
- Dynamic thresholds adjust behavior across short/long windows

Artifacts
- Metrics/guardrails JSON validated; failing runs surface reason codes
- Calibration harness runs produce report; thresholds updated and documented

