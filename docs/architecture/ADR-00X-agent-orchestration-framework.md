# ADR-00X: Agent Orchestration Framework

Status: Proposed
Date: 2025-10-10
Decision drivers: Simplicity, determinism, testability, no extra infra

Context
- Epics 16/21 require an “Agentic Mode” where a server-side orchestrator proposes a run plan (universe, strategies, params, guardrails) and, on user click, starts runs.
- Options considered: LangGraph, lightweight internal orchestrator, CrewAI/LlamaIndex agents, Temporal (durable workflows).

Options
1) Lightweight internal orchestrator (current codebase)
   - Implement as a small service module (backend/services/agentic.py) with two entry points:
     - propose_plan(from_date, to_date) → PlanV1
     - start_agentic_run(plan | plan_id) → { run_ids }
   - Universe discovery via filesystem scan of warehouse (Epic 18); guardrails implemented as pure functions (Epic 19).
   - Leverage existing backtest creation path (create_backtest_service) to enqueue runs/jobs; persist plan/guardrail results into manifest.
   - Pros: Minimal dependencies, deterministic, easy to test and evolve. Fits MVP.
   - Cons: No built-in durability/saga primitives; manual retries/backpressure.

2) LangGraph-based agent graph
   - Pros: Rich agent flows with state machines.
   - Cons: New dependency, learning curve, persistence decisions, limited value at MVP.

3) Temporal (durable workflows)
   - Pros: First-class durability, retries, backpressure, visibility.
   - Cons: Infra heavy, adds server and SDK, not justified for single-node MVP.

Decision
- Choose Option 1 (lightweight internal orchestrator) for Epics 16–21.
- Encapsulate in backend/services/agentic.py; expose FastAPI routes under /api/v1/agentic.
- Persist plan + guardrail results in run-manifest; keep manual mode unaffected.

Consequences
- Fast time-to-value; no extra infra.
- If/when we need durable campaigns or background auto-runs, revisit (Temporal or equivalent).
- Keep code structured so that flows can migrate to an engine later without breaking APIs.

Implementation notes
- PlanV1 includes: inputs, discovered universe with coverage%, selected strategies (from StrategyRegistry), guardrail results, and decision explanations.
- start_agentic_run submits N runs (per symbol × strategy) initially. Epic 20 will enable multi-strategy bundles in one run.
- Feature flag gate (server + UI) to hide endpoints/toggle when off; consent recorded in manifest when Start is invoked.

