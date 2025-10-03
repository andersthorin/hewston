# RFC: Repository Architecture Modernization (Hexagonal + Modular)
> Note: This RFC content has been folded into PRD Epic 12 for canonical reference: ../prd/epic-12-code-cleanup-and-architectural-alignment.md



Date: 2025-10-03
Status: Draft
Authors: Augment Agent (Architect), Team
Reviewers: TBD
Target Window: Q4 2025 (pilot), rolling into Q1 2026 (batch)

## Summary
Modernize the repository to a modular, Hexagonal architecture across backend and BFF, and a component-/feature-centric frontend with clear boundaries, aliases, and co-located unit tests. Maintain non-breaking behavior with an incremental, low-risk migration.

## Goals
- Feature modules with domain/application/ports/adapters/infrastructure (backend & BFF)
- Frontend: component-/feature-centric directories; TS path aliases; boundary rules
- UI components remain "dumb" (presentational): logic externalized to hooks/containers/services
- Co-locate unit tests; centralize e2e/integration in tests/
- Keep CI green with small, reversible PRs

## Non-Goals
- Code changes beyond the pilot until ADRs approved
- Breaking API changes (unless captured in future ADRs)

## Motivation
- Reduce coupling and improve change velocity
- Clearer ownership and review boundaries per feature/module
- Enhanced testability and reliability

## Detailed Design
### Repository Structure
- Backend/BFF: modules/<feature>/{domain, application (ports), adapters, infrastructure}
- Frontend: src/components/<kebab> and src/features/<feature>; barrels and aliases

### Frontend Principles
- Components are "dumb": driven by props, minimal local UI state only
- Data fetching, orchestration, and global state live in hooks/containers/services
- Use @components, @features, @utils, @services path aliases

### Backend/BFF Principles
- Application layer defines use-cases and ports; adapters implement
- Controllers are thin; wiring lives in infrastructure/app
- Avoid cross-service imports (BFF does not use backend internals)

### Tests
- Unit: co-located *.test.tsx / *.test.py
- Integration: tests/integration/<area>
- E2E: tests/e2e (or per-app e2e folders if needed)

## Phased Plan
1) Approve ADR-001/002/003
2) Pilot: Frontend RunsTable; Backend and BFF backtests module
3) Batch: module-by-module moves, update imports and aliases
4) Guardrails: ESLint boundaries (FE), import-direction checks (BE/BFF)
5) Final validation and documentation updates

## Risks and Mitigations
- Broken imports after moves: codemods, alias support, small PRs
- Hidden cross-module dependencies: temporary re-exports; deprecation windows
- Resistance to structure changes: clear docs, PR templates, examples

## Alternatives Considered
- Continue with layer-centric structure: rejected due to scaling risks
- Big-bang refactor: rejected due to high risk

## Rollback Strategy
- Each PR small and reversible; revertible without cascading changes
- Keep pre-move paths temporarily via re-exports when needed

## Acceptance Criteria (Definition of Done)
- CI builds and tests pass
- No unresolved imports; aliases validated
- Pilot modules reflect agreed structure; sample diffs captured
- Docs updated: Architecture.md, module READMEs, ADRs; onboarding guide added

## Open Questions
- Final naming for top-level module folders (modules/ vs src/modules/)
- Which modules/components to prioritize after pilot
- Timing for enabling guardrails in CI

