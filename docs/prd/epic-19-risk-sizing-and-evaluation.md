# Epic 19 — Risk, Sizing, and Evaluation (Backtests Only)

Goal
- Establish consistent position sizing, portfolio/risk constraints, and evaluation metrics with guardrails for fully agentic backtests started by the user.

Why (Value)
- Comparable, realistic results; safety against pathological strategies; strong ranking/reporting.

Scope (In)
- Sizing policies:
  - Volatility-normalized target risk per trade (e.g., 10 bps/day), with floors/ceilings
  - Fixed-size fallback if vol is unavailable
- Risk constraints:
  - Per-symbol max exposure; account-level gross/net exposure caps
  - EOD flatten option for intraday/quotes
  - Max drawdown stop per run (e.g., 25%)
  - Daily trade count cap (anti-pathology)
- Evaluation metrics suite:
  - Return, Annualized return, Volatility, Sharpe/Sortino
  - Max Drawdown, Calmar
  - Hit rate, Profit factor
  - Turnover, Cost-adjusted PnL (slippage/fees simulation)
- Guardrails (enforced pre/post):
  - Min data coverage (from Epic 18)
  - Min trade count per strategy (e.g., 30) or per-day minimum
  - Max turnover, no NaN metrics

Scope (Out)
- Broker margin/borrowing models (future)

Realism for future multi-symbol live/paper parity
- Simulate shared capital and competition across strategies:
  - Prefer per-symbol multi-strategy runs with OMS=HEDGING to share account
  - For multi-symbol bundles, apply account-level caps and slippage/cost models across the bundle
- Bias mitigation and validation:
  - Cross-section sampling (rotate symbols in bundles)
  - Walk-forward splits and rolling windows
  - Correlation stress tests across symbols

Acceptance Criteria
- Policies configurable via code/config; applied consistently in backtests
- Metrics.json persisted per run and used for ranking
- Guardrails reject/flag unstable plans with clear reasons

Milestones
1) Implement sizing policies and caps
2) Implement metrics suite and cost simulation
3) Guardrail checks and wiring to orchestrator
4) Ranking and summary report in UI

