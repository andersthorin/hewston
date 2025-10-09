# ADR-005 — Metrics and Guardrails Baseline

Status
- Proposed

Context
- Agentic backtests must be realistic and comparable. We need consistent metric definitions and guardrail thresholds which scale with window length and data quality.

Decision
- Establish a baseline metrics and guardrails specification for equities/XNAS backtests on quotes-derived mid-returns.

Definitions
- Returns: log returns on mid-price (mid = (bid+ask)/2).
- Volatility: realized vol on mid-returns; default EWMA(λ=0.94) or rolling std(window=20 days), configurable.
- KPIs: Total Return, Ann. Return, Ann. Volatility, Sharpe, Sortino, Max Drawdown, Calmar, Hit Rate, Profit Factor, Turnover, Trade Count.
- Cost-adjusted PnL: PnL minus cost model (see ADR-006).

Guardrails (baseline)
- Coverage: ≥ 90% of trading days over [from, to] (see ADR-007).
- Min sample size: trades_per_day ≥ 1 on average OR total_trades ≥ 30 for the window.
- Turnover cap: configurable; default conservative to curb micro-structure overfit.
- Max drawdown stop: default 25% at run level (configurable).
- Invalid metrics: reject if NaN/inf appears in critical KPIs.


Defaults (initial)
- Coverage threshold: 90% of NYSE trading days (see ADR-007)
- Min trades: ≥ 30 total OR ≥ 1 per trading day on average
- Max drawdown stop: 25% run-level
- Turnover cap: target 10–15× per month equivalent (configurable)
- Reject invalid KPIs (NaN/inf) in Sharpe/Sortino/MaxDD/Turnover

Dynamic thresholds
- For short windows (< 20 trading days): lower absolute trade count threshold but enforce trades_per_day ≥ 1.
- For long windows (> 120 trading days): require total_trades ≥ 60 and tighten turnover cap by 10%.

Observability
- Persist metrics.json with raw and cost-adjusted metrics, plus metadata: method = {ewma|rolling}, window, λ.
- Persist guardrail evaluations with reason codes and details.

Consequences
- Orchestrator can enforce realism automatically and explain exclusions.
- Comparisons across runs will be fairer and reproducible.

Migration
- Start with defaults above; tune thresholds empirically via calibration harness (Story 19.5).

Links
- ADR-006 Cost Model Calibration
- ADR-007 Trading-Day Coverage Definition
- Epic 19 PRD/Plan

