# ADR-004 — Agent Orchestration Framework for Agentic Backtests

Status
- Proposed

Context
- Scope: Backtests only (no paper/live), user always starts the run. Equities/XNAS only. M1 laptop constraints.
- Requirements: Deterministic, auditable planning (universe/strategies/params), guardrails, manifest persistence, minimal operational complexity.
- Near-term capabilities: Single process service can generate a plan and kick off jobs; no long-running conversational agents required; flows are short-lived and synchronous from the UI.

Decision
- Start with a lightweight internal orchestrator (policy modules + typed services) and defer adopting a dedicated agent graph/runtime (e.g., LangGraph) until complexity warrants.

Rationale
- Determinism & Auditability: Internal policy modules (pydantic-validated) provide reproducible decisions and easy diff/manifest logging.
- Complexity Fit: Our current flows are short-lived and user-triggered; we do not need stateful, multi-turn tool choreography.
- Performance/Footprint: Avoids adding a heavy runtime on M1; keeps latency and memory predictable.
- Extensibility: We can wrap/compose policies now and migrate to a graph framework later if we introduce multi-agent tool flows, retries, or human-in-the-loop branching.

Options Considered
1) Lightweight Internal Orchestrator (Chosen)
   - Pros: Simple, typed, deterministic; easiest to test and review; minimal infra.
   - Cons: Less built-in support for complex tool graphs and retries.
2) LangGraph (LLM-driven stateful graphs)
   - Pros: Strong for complex, tool-rich agent workflows with memory and control flow.
   - Cons: Adds runtime complexity and cost; overkill for short, deterministic planning.
3) CrewAI / LlamaIndex Agents
   - Pros: Quick to prototype multi-agent collaboration.
   - Cons: Additional abstractions, less control/determinism for compliance-grade guardrails.
4) Temporal (durable workflow engine)
   - Pros: Great for long-running, reliable workflows with retries and human tasks.
   - Cons: Infrastructure overhead and operational complexity not justified yet.

Consequences
- We implement planning as pure code (functions/classes) with configuration and guardrails checked into the repo.
- Agentic Mode remains fully user-triggered; manifests record inputs, decisions, guardrail outcomes, and code hash.
- If/when we add multi-agent, long-running flows (e.g., research → propose → review → revise), we will reassess adopting LangGraph or Temporal.

Implementation Plan
- Create a small orchestrator package (backend/orchestrator):
  - universe.py: discovery, coverage %, filters, reasons (Epic 18)
  - strategies.py: registry lookups, defaults, per-symbol instantiation plan (Epics 17, 20)
  - risk.py: sizing policy selection and caps (Epic 19)
  - guardrails.py: checks with reason codes (Epic 19)
  - planner.py: propose_plan(from, to) → PlanJSON
  - executor.py: start_agentic_run(plan) → run_ids + manifests
- Pydantic models for Plan, GuardrailResult, StrategySpec, UniverseSelection.
- Persist PlanJSON + GuardrailResults alongside run manifests.

Review Criteria
- Determinism: Same inputs → same plan; unit tests cover edge cases.
- Observability: Plan and guardrail reasons are persisted and human-readable.
- Safety: Guardrails prevent unrealistic runs; thresholds configurable.
- Extensibility: Clear seams to swap in LangGraph/Temporal if needed.

Decision Drivers to Revisit
- When agent flows span multiple steps and time (research, negotiation, retries, approvals)
- When we need durable execution, high fan-out/fan-in with robust retries
- When we need rich tool graphs or cross-agent memory beyond simple policies

Links
- Related PRDs: Epics 16–21
- Runner Design: Epic 20 plan and PRD
- Guardrails & Metrics: Epic 19 plan and PRD

