# Epic 21 Plan — Agentic Ops and Guardrails (Backtests Only)

Objective
- Provide an Agentic Mode operational flow where the user starts runs; apply guardrails; maintain history/audit. Decide agent orchestration framework via ADR.

Phases and Tasks
1) Ops surface (owner: FE)
   - UI toggle for Agentic Mode; Plan Preview panel; results ranking
2) Guardrails & history (owner: BE)
   - Enforce pre/post checks with reason codes
   - Persist manifests (plan, guardrails, code hash, inputs)
3) ADR: Orchestration framework (owner: Architect)
   - Evaluate LangGraph vs lightweight internal orchestrator vs alternatives (CrewAI, LlamaIndex Agents, Temporal)
   - Decision matrix and recommendation; document ADR-00X
4) Insights (owner: BE/FE)
   - Summaries: top symbols/strategies, stability flags, cost sensitivity

Dependencies
- Epics 16, 18, 19, 20

Acceptance Criteria
- User must click Start; guardrails enforced; manifests persisted and browseable
- ADR documented and linked from epic
- Results view shows ranking and key insights

