# Epic 21 — Agentic Ops and Guardrails (Backtests Only)

Goal
- Provide an “Agentic Mode” operational surface where the user starts runs, but universe/strategy/params are selected automatically within guardrails. No fully autonomous scheduling yet.

Why (Value)
- Faster experimentation with safety and auditability; retains explicit user intent to start runs.

Scope (In)
- Commands/flows:
  - Propose Plan (server-side; not user-visible unless Plan Preview open)
  - Start Agentic Run (user click triggers execution if guardrails pass)
  - Summarize Results (post-run ranking + insights)
- Guardrails and thresholds (see Epic 19) applied pre-run and validated post-run
- History & reproducibility:
  - Manifests with plan, guardrail results, code hash, inputs; visible in UI
- UI additions:
  - Agentic Mode toggle; Plan Preview panel; Results summary with ranking criteria

Scope (Out)
- Autonomous background scheduling or cron-like campaigns
- Paper/live trading automation (future)

Open Decisions & ADRs
- Agent orchestration framework: LangGraph vs lightweight internal orchestrator vs alternatives (CrewAI, LlamaIndex Agents, Temporal). Assign to Architect Agent; capture in ADR-00X.
- Default guardrail thresholds and how they may vary by strategy family.

Acceptance Criteria
- Agentic Mode available; user must click Start to execute plan
- Guardrails enforced; failures explained; artifacts persisted with manifests
- Results summarized with ranking and downloadable artifacts

Milestones
1) UI: toggle + Plan Preview + Start flow
2) Guardrail enforcement in orchestrator
3) Manifest + history + results summary
4) ADR for orchestration framework

