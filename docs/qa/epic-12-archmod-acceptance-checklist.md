# Epic 12 — Acceptance Checklist: Code Cleanup and Architectural Alignment

Use this checklist to validate completion of Epic 12 across backend, BFF, and frontend.

## Governance & Documentation
- [ ] ADR-001/002/003 approved and linked in PRs
- [ ] Epic 12 updated with final links to ADRs, stories, and architecture docs
- [ ] Architecture.md updated (Related Docs section)

## Frontend (UI Components are “Dumb”)
- [ ] Components are presentational: props-in/callbacks-out; minimal local UI state
- [ ] No direct data-fetching or global state in components; logic in hooks/containers/services
- [ ] Path aliases configured and used (@components, @features, @utils, @services)
- [ ] Unit tests colocated; broader tests in tests/integration or tests/e2e

## Backend/BFF (Hexagonal Boundaries)
- [ ] Per-feature modules exist (domain, application, adapters, infrastructure)
- [ ] Application layer defines ports and use-cases; no framework imports in domain/application
- [ ] Adapters implement ports; controllers are thin
- [ ] No imports from adapters/infrastructure into domain/application
- [ ] Cross-module interactions via explicit ports/public APIs (no deep imports)

## Validation (Builds/Tests/Imports)
- [ ] CI builds green (frontend + backend + BFF)
- [ ] Unit/integration/e2e pass (where present)
- [ ] No unresolved imports after moves (TS and Python)
- [ ] Sample diffs included in pilot PRs and documented in epic

## Guardrails (after sign-off)
- [ ] ESLint boundaries enabled (frontend) and passing
- [ ] Import-direction checks for backend/BFF (no inward violations)

## Risk & Rollback
- [ ] Small and reversible PRs; rollback plan documented in epic
- [ ] Temporary re-exports/aliases documented with cleanup follow-ups

