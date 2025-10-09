# Epic 19 Plan — Risk, Sizing, and Evaluation

Objective
- Implement sizing policies, risk constraints, metrics suite, and guardrails for agentic backtests.

Phases and Tasks
1) Sizing policies (owner: BE)
   - Volatility-normalized target risk per trade; floors/ceilings
   - Fixed-size fallback
   - Pluggable policy selection via config
2) Risk constraints (owner: BE)
   - Per-symbol exposure caps; account-level caps; EOD flatten
   - Max drawdown stop; daily trade count cap
3) Metrics & costs (owner: BE)
   - Return, annualized vol, Sharpe/Sortino, MaxDD, Calmar, hit rate, profit factor
   - Turnover; slippage/fees simulation (configurable model)
   - Persist metrics.json per run
4) Guardrails (owner: BE)
   - Coverage %, min trades, turnover cap, NaN checks
   - Guardrail evaluations with reason codes
5) UI (owner: FE)
   - Results summary & ranking; thresholds visualization

Dependencies
- Epic 18 (coverage), Epic 20 (portfolio context)

Acceptance Criteria
- Policies configurable and enforced; metrics persisted
- Guardrails integrated with orchestrator and visible in UI

