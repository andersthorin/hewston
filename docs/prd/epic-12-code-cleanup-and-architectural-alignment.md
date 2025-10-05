# Epic 12 — Code Cleanup and Architectural Alignment

Date: 2025-10-03
Status: Draft

Objective: Align the repository with Hexagonal (Ports & Adapters) and modular architecture, clean up cross-cutting utilities, and adopt a component-/feature-centric frontend while keeping UI components "dumb". Deliver docs, a low-risk pilot, batch refactors, and guardrails.

## Success Metrics
- CI green after each phase
- Reduced cross-module imports/utilities
- Clear per-feature modules; co-located unit tests

## Documentation Package Overview
- Architecture Review Report: [docs/architecture/000-architecture-review-report.md](../architecture/000-architecture-review-report.md)
- Target Architecture & Conventions: [docs/architecture/010-target-architecture-and-conventions.md](../architecture/010-target-architecture-and-conventions.md)
- Migration Plan & Governance: [docs/architecture/020-migration-plan-and-governance.md](../architecture/020-migration-plan-and-governance.md)
- ADRs: [ADR-001](../architecture/ADR-001-directory-strategy-and-hexagonal-boundaries.md), [ADR-002](../architecture/ADR-002-frontend-path-aliases-and-boundary-enforcement.md), [ADR-003](../architecture/ADR-003-backend-bff-module-extraction-strategy.md)
- Review Checklist: [docs/architecture/review-checklist.md](../architecture/review-checklist.md)
- QA Acceptance Checklist: [docs/qa/epic-12-archmod-acceptance-checklist.md](../qa/epic-12-archmod-acceptance-checklist.md)

## Business Value
- Engineering velocity: smaller PR blast radius via clear module boundaries
- Reliability: stricter layering enables isolated tests and safer refactors
- Onboarding: discoverable structure, co-located tests, and clear docs

## Technical Approach
- Per-feature modules with hexagonal layering in backend/BFF
- Component-/feature-centric frontend; "dumb" components principle; TS path aliases

## Start Here: Pilot Work Orders (Dev)
- Frontend Pilot (RunsTable): see Story 12.4 — implement presentational component + extract logic to hook/service; add colocated unit test; alias imports.
- Backend Pilot (Backtests exemplar): see Story 12.4 — create modules/backtests/{domain,application,adapters,infrastructure}; move one use‑case with port+adapter; thin controller; infra wiring; add module README.
- BFF Pilot (Backtests outbound gateway): see Story 12.4 — add module skeleton, httpx gateway; decouple logging; preserve endpoints; add module README.

Note: Do not change APIs or add deps/tooling without explicit approval. Keep PRs small and revertible.

- Incremental migration: pilot → batch → guardrails; ADR/RFC governance

## Key Deliverables
1. Architecture docs and ADRs approved
2. Pilot refactor (RunsTable; backtests module in backend/BFF)
3. Batch module refactors and import updates
4. Guardrails: ESLint boundaries; import-direction checks (proposal)
5. Updated docs (Architecture.md, module READMEs, onboarding)


## Dev Handoff

Non‑Goals (enforced)
- No API changes unless explicitly ADR’d and approved
- No new dependencies or tooling enablement without explicit approval

Repository‑wide inclusion criteria (what gets refactored)
- Frontend
  - Any component containing data‑fetching/global state or orchestration logic (move to hooks/containers/services)
  - Cross‑feature deep imports; replace with aliases (@components, @features, @utils, @services)
  - Components missing colocated unit tests
- Backend/BFF
  - Domain/application importing adapters/infrastructure/frameworks (violation → fix via ports/adapters)
  - Cross‑module deep imports; reduce via public APIs/barrels
  - Oversized shared utils that bleed boundaries

Pilot PR plan (Story 12.4)
- Frontend (RunsTable)
  - Create feature folder and barrel; keep component presentational (props‑in/callbacks‑out)
  - Extract data‑fetching/state to hook/service; add colocated unit test
  - Update imports to use aliases; keep behavior unchanged
- Backend (Backtests module exemplar)
  - Create modules/backtests/{domain,application,adapters,infrastructure}
  - Move one use‑case and its port + adapter; keep controller thin, wiring in infrastructure
  - Preserve existing API surface; add module README
- BFF (Backtests outbound gateway)
  - Add module skeleton and httpx gateway; decouple logging from backend
  - Preserve endpoint contracts; add module README

Batch refactor playbook (Story 12.5)
- One feature/module per PR; introduce public barrels; update imports
- Use temporary re‑exports if needed; remove in follow‑ups
- Keep CI green; no functional changes

Codemod strategy (proposal only; do not run without approval)
- Frontend: alias rewrites and extraction helpers (ts‑morph/jscodeshift outline)
- Backend/BFF: safe Python import updates; barrel introduction script outline

PR checklist (apply to every PR)
- No API surface changes; no new deps/tooling
- Aliases used; no deep cross‑module imports
- Domain/application free of framework/adapters imports
- Colocated unit tests added/updated
- CI build/test/lint pass; no unresolved imports
- Update Architecture.md or module README if structure changed

Validation
- Pilot completion: import graph delta shows fewer cross‑module imports; no new cycles
- Batch: track boundary violations; add waivers only with short‑term cleanup tasks

## Stories (linked)
- Story 12.1 — Inventory & Architecture Review Report: [docs/stories/12.1.story.md](../stories/12.1.story.md)
- Story 12.2 — Target Architecture & Conventions: [docs/stories/12.2.story.md](../stories/12.2.story.md)
- Story 12.3 — Migration Plan & Governance (ADRs + RFC): [docs/stories/12.3.story.md](../stories/12.3.story.md)
- Story 12.4 — Pilot Refactor (Frontend + Backend + BFF): [docs/stories/12.4.story.md](../stories/12.4.story.md)
- Story 12.5 — Batch Refactors (Per Module): [docs/stories/12.5.story.md](../stories/12.5.story.md)
- Story 12.6 — Tooling & Guardrails: [docs/stories/12.6.story.md](../stories/12.6.story.md)
- Story 12.7 — Documentation & Knowledge Transfer: [docs/stories/12.7.story.md](../stories/12.7.story.md)
- Story 12.8 — Validation: [docs/stories/12.8.story.md](../stories/12.8.story.md)

## Appendix A — RFC (Folded here)

This appendix folds the RFC content into the Epic to align with PRD-centric documentation.

## RFC: Code Cleanup and Architectural Alignment (Hexagonal + Modular)

Date: 2025-10-03
Status: Draft
Authors: Augment Agent (Architect), Team
Reviewers: TBD
Target Window: Q4 2025 (pilot), rolling into Q1 2026 (batch)

### Summary
Modernize the repository to a modular, Hexagonal architecture across backend and BFF, and a component-/feature-centric frontend with clear boundaries, aliases, and co-located unit tests. Maintain non-breaking behavior with an incremental, low-risk migration.

### Goals
- Feature modules with domain/application/ports/adapters/infrastructure (backend & BFF)
- Frontend: component-/feature-centric directories; TS path aliases; boundary rules
- UI components remain "dumb" (presentational): logic externalized to hooks/containers/services
- Co-locate unit tests; centralize e2e/integration in tests/
- Keep CI green with small, reversible PRs

### Non-Goals
- Code changes beyond the pilot until ADRs approved
- Breaking API changes (unless captured in future ADRs)

### Motivation
- Reduce coupling and improve change velocity
- Clearer ownership and review boundaries per feature/module
- Enhanced testability and reliability

### Detailed Design
#### Repository Structure
- Backend/BFF: modules/<feature>/{domain, application (ports), adapters, infrastructure}
- Frontend: src/components/<kebab> and src/features/<feature>; barrels and aliases

#### Frontend Principles
- Components are "dumb": driven by props, minimal local UI state only
- Data fetching, orchestration, and global state live in hooks/containers/services
- Use @components, @features, @utils, @services path aliases

#### Backend/BFF Principles
- Application layer defines use-cases and ports; adapters implement
- Controllers are thin; wiring lives in infrastructure/app
- Avoid cross-service imports (BFF does not use backend internals)

#### Tests
- Unit: co-located *.test.tsx / *.test.py
- Integration: tests/integration/<area>
- E2E: tests/e2e (or per-app e2e folders if needed)

### Phased Plan
1) Approve ADR-001/002/003
2) Pilot: Frontend RunsTable; Backend and BFF backtests module
3) Batch: module-by-module moves, update imports and aliases
4) Guardrails: ESLint boundaries (FE), import-direction checks (BE/BFF)
5) Final validation and documentation updates

### Risks and Mitigations
- Broken imports after moves: codemods, alias support, small PRs
- Hidden cross-module dependencies: temporary re-exports; deprecation windows
- Resistance to structure changes: clear docs, PR templates, examples

### Alternatives Considered
- Continue with layer-centric structure: rejected due to scaling risks
- Big-bang refactor: rejected due to high risk

### Rollback Strategy
- Each PR small and reversible; revertible without cascading changes
- Keep pre-move paths temporarily via re-exports when needed

### Acceptance Criteria (Definition of Done)
- CI builds and tests pass
- No unresolved imports; aliases validated
- Pilot modules reflect agreed structure; sample diffs captured
- Docs updated: Architecture.md, module READMEs, ADRs; onboarding guide added

### Open Questions
- Final naming for top-level module folders (modules/ vs src/modules/)
- Which modules/components to prioritize after pilot
- Timing for enabling guardrails in CI

