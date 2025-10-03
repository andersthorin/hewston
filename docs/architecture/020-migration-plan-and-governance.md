# Migration Plan (Incremental) & Change Governance

Date: 2025-10-03

## 1. Principles
- Non-breaking, incremental PRs.
- Pilot first, then batch. Keep CI green at each step.
- Prefer additive moves (new folders + imports updated) over large renames.

## 2. Phases
- Phase 0: Confirm assumptions and constraints (Q&A).
- Phase 1: Review & inventory (this is done; see 000-Architecture Review Report).
- Phase 2: Draft target structure & conventions (see 010-Target Architecture).
- Phase 3: ADRs + RFC authored for fast feedback.
- Phase 4: Pilot refactor (frontend + backend + BFF examples).
- Phase 5: Batch refactors module-by-module; update imports/aliases.
- Phase 6: Introduce guardrails (lint/boundaries) after sign-off.
- Phase 7: Final validation & sign-off; summarize outcomes.

## 3. Pilot (Low-Risk Examples)
### 3.1 Frontend: RunsTable component
- Create src/components/runs-table/ with:
  - RunsTable.tsx (moved from src/components/RunsTable.tsx)
  - RunsTable.test.tsx (moved/renamed from RunsTable.test.tsx if present)
  - index.ts (barrel)
- Update imports to use @components alias (proposal).

Sample diff (illustrative):

```diff
- import RunsTable from "../components/RunsTable"
+ import { RunsTable } from "@components/runs-table"
```

### 3.2 Backend: Backtests module
- Create backend/modules/backtests/{domain,application/ports,adapters,infrastructure}.
- Move relevant files:
  - backend/ports/backtest_runner.py -> modules/backtests/application/ports/runner.py
  - backend/adapters/nautilus.py -> modules/backtests/adapters/nautilus_runner.py
  - backend/api/routes/backtests.py -> api keeps router but delegates to adapters/http/controllers.py
- Introduce a use-case in application/use_cases (e.g., list_backtests.py).
- Wire module in infrastructure/wiring.py and hook into FastAPI route handler.

### 3.3 BFF: Backtests module
- Create bff/modules/backtests/... mirroring backend layering.
- Define outbound port (backend_gateway.py) and implement httpx adapter.
- Move bff/api/backtests.py controller logic into adapters/http/controllers.py (thin), delegating to application use-cases.
- Remove dependency on backend.app.logging_setup; own logging configuration in BFF infra.

## 4. Batch Rollout
- Repeat module extraction for catalog, market-data, etc.
- Frontend: migrate prioritized components and introduce features/ where applicable.
- Introduce TS path aliases; update import paths via codemod/script.
- Reduce backend shared utils/services by inlining into modules or formalizing ports.

## 5. Enforcement (Proposal; no changes until approved)
- Frontend: Add ESLint rules (e.g., boundaries) to prevent cross-feature imports except via index.ts.
- Backend/BFF: Add simple static checks for import directions (e.g., script that forbids domain importing adapters).
- CI: Run these checks along with existing tests/linters.

## 6. Risks & Rollback Strategy
- Risks: Broken imports, un-wired dependencies, unnoticed cross-module coupling.
- Mitigations:
  - Small PRs per module/component.
  - Keep old paths temporarily with re-exports if needed (deprecation window).
  - Validate with unit/integration tests and smoke run.
- Rollback: Revert PR or re-point imports to prior locations; maintain branch strategy.

## 7. Change Governance
### 7.1 ADRs to Author
- ADR-001: Repository directory strategy & hexagonal boundaries.
- ADR-002: Frontend TS path aliases & import boundary enforcement.
- ADR-003: Backend/BFF module extraction strategy (ports/adapters, wiring patterns).

Each ADR should include: context, decision, consequences, alternatives, and migration impact.

### 7.2 RFC
- RFC: Repository Architecture Modernization
  - Problem statement, scope, phased plan, risks, roll-back, and acceptance criteria.
  - Links to ADRs and sample diffs.

### 7.3 Review Checklist (lightweight)
- Non-breaking; tests green.
- Imports resolved; no adapter/domain direction violations.
- Docs updated (Architecture.md, module READMEs).

## 8. Validation & Definition of Done
- CI builds & tests (unit/integration/e2e) pass.
- No unresolved imports; aliases validated.
- Pilot modules reflect agreed structure; sample diffs captured in PR descriptions.
- Docs updated: repo Architecture.md, per-module READMEs, ADRs.
- Onboarding guide available (how to add a new component/module).

## 9. Next Steps (Actions)
1) Approve ADR/RFC drafts.
2) Execute pilot (frontend RunsTable; backend & BFF backtests).
3) Evaluate feedback/metrics; proceed with batch refactors.
4) Introduce guardrails; monitor violations.

