# Epic 20 — Nautilus Multi‑Strategy Runner (Equities/XNAS)

Goal
- Execute multiple strategy instances per symbol in a single backtest run, with optional small multi‑symbol bundles, using Nautilus Trader. Support streaming/batching for M1 resource limits.

Why (Value)
- Enables realistic interaction of strategies on the same symbol/account and scalable exploration across symbols.

Scope (In)
- Runner API updates (backend/adapters/nautilus.py):
  - Accept `instrument_ids: list[str]` and `strategies: list[StrategySpec]`
  - Instantiate one strategy per (symbol × strategy) when strategy is single‑instrument
  - Build BacktestRunConfig with multiple strategies + data configs (QuoteTicks)
  - OMS=HEDGING, add strategies before data (subscriptions)
  - Optional `streaming=True` for large ranges
- Job integration (backend/jobs/run_backtest.py):
  - Accept plan with many runs or bundled runs; persist artifacts and manifest per run
- Metrics aggregation:
  - Per‑strategy and portfolio‑level metrics from engine; fall back to equity/fills analysis

Scope (Out)
- Cross‑instrument strategies (defer)
- Non‑equities venues

Realism & Scaling
- Prefer per‑symbol multi‑strategy bundles; small multi‑symbol bundles when memory allows
- Shared account constraints (see Epic 19) when multiple strategies run together
- Calibrate slippage/fees assumptions; include turnover guardrails

Acceptance Criteria
- A single run can execute multiple strategies on a symbol; artifacts persisted
- Optional: a single run can include a small bundle of symbols
- Streaming mode validated on longer ranges

Milestones
1) Extend runner: multiple strategies + multiple instrument_ids
2) BacktestRunConfig wiring + streaming mode
3) Metrics extraction and aggregation
4) Job integration and manifest updates

