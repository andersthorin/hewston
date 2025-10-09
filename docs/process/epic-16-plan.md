# Epic 16 Plan — Agentic Backtest Orchestrator (Equities/XNAS)

Objective
- User-triggered Agentic Mode with guardrails; manual mode preserved.

Phases and Tasks
1) UI surface (owner: FE)
   - Add Agentic Mode toggle; preserve manual controls (symbol+strategy+dates)
   - Date range picker; validation
   - Wire to backend endpoints
2) Orchestrator (owner: BE)
   - propose_plan(from,to): returns universe, strategies, params, guardrail checks
   - start_agentic_run(plan_id or payload): enqueues runs; returns manifest path
3) Guardrails (owner: BE)
   - Coverage %, min trades, turnover cap, max DD stop, NaN checks
   - Reason codes and explanations
4) Persistence (owner: BE)
   - Store plan JSON, guardrail results, code hash in run-manifest
   - Expose in list/detail APIs
5) UI Plan Preview + Start (owner: FE)
   - Collapsible plan preview
   - “Start Agentic Run” button (no auto-start countdown)
6) Results summary (owner: FE+BE)
   - Rank runs by KPIs; link to artifacts

Dependencies
- Epic 18 (universe discovery), Epic 19 (guardrails/metrics), Epic 20 (runner multi-strategy)

Acceptance Criteria
- Agentic Mode ON: user selects dates → Start Agentic Run triggers runs within guardrails
- Manual mode unchanged and working
- Plan + guardrail results persisted and viewable

Risks/Mitigations
- Data gaps → coverage check and reasons
- Memory on M1 → small bundles; streaming support (Epic 20)

Deliverables
- New FE toggle and preview
- propose_plan and start_agentic_run endpoints
- Run manifests with plan + guardrails + code hash

