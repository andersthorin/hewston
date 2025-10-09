# Epic 16 — Agentic Backtest Orchestrator (Equities/XNAS)

Goal
- Allow the admin/user to start a backtest campaign from the UI by selecting only a date range when "Agentic Mode" is ON. The system auto-selects universe (symbols), strategies, parameters, and risk caps within guardrails. Manual mode (current behavior) remains available: select symbol + strategy + date range.

Why (Value)
- Dramatically reduces friction to explore the space of strategies/symbols while maintaining safety and reproducibility. Keeps manual control for targeted runs.

Scope (In)
- UI changes:
  - Agentic Mode toggle on the create-run screen
  - Date-range picker (from/to)
  - Optional collapsible "Plan Preview" with proposed universe, strategies, parameters, and guardrail checks
  - Single "Start Agentic Run" button (user-triggered; no autonomous scheduling)
- Backend Orchestrator service:
  - Generates a proposed plan given date range and data availability
  - Validates plan against guardrails (coverage %, min trades per strategy, max turnover, etc.)
  - On user start, submits one or multiple backtest runs (based on bundling strategy)
  - Persists plan and guardrail checklist into run-manifest
- Governance / Reproducibility:
  - Persist code hash and plan manifest
  - Keep manual mode intact alongside agentic mode

Scope (Out)
- Paper/live trading automation (future; not in this epic)
- Non-equities venues (keep to XNAS)

Guardrails (initial)
- Data coverage per symbol in range >= 90%
- Strategy produces >= 30 trades in the period (or per-day minimum for intraday)
- Turnover cap (configurable), reject degenerate scalpers in quotes-only runs
- Max drawdown stop per run (configurable; e.g., 25%)
- Reject runs with NaN/invalid metrics

Architecture/Design
- Orchestrator generates a Run Plan:
  - Universe discovery: list available symbols under data/warehouse/quotes/venue=XNAS/symbol=*/date=*
  - Strategy set and defaults (from StrategyRegistry); parameter defaults per strategy
  - Bundling policy: per-symbol multi-strategy runs; optionally small multi-symbol bundles if memory allows
  - Risk policy (see Epic 19): volatility-normalized sizing or fixed-size fallback; EOD flatten for intraday
  - Guardrail checks pre-run; explain reasons for excluded symbols/strategies
- Persist Plan:
  - Store plan JSON (inputs, decisions, guardrail results) with run-manifest

Open Decisions (record via ADR) — see docs/architecture/ADR-00X-agent-orchestration-framework.md
- Agent orchestration framework: LangGraph vs lightweight internal orchestrator vs alternatives (CrewAI, LlamaIndex Agents, Temporal for durable flows). Architect Agent to recommend and author ADR.
- Plan Preview: optional countdown auto-start vs immediate start on click (for now: immediate start on click; no auto-start countdown)

Acceptance Criteria
- UI shows Agentic Mode toggle; manual mode (symbol+strategy) remains fully functional
- With Agentic Mode ON, user selects date range and clicks Start Agentic Run; system creates runs without additional prompts
- Plan Preview available; plan + guardrail results saved in manifest
- Guardrails enforced; rejected items listed with reasons

Milestones
1) UI toggle + form wiring (manual mode unchanged)
2) Orchestrator endpoint: propose plan + run plan
3) Guardrail implementation + explanations
4) Manifest persistence (plan, guardrails, code hash) and UI surface

Notes
- User always starts backtests (no autonomous scheduling in this epic)
- Equities-only (XNAS) per user guidance

