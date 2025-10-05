# Architecture Modernization Review Checklist

Use this checklist when reviewing PRs related to the Hexagonal + Modular restructuring and frontend component/feature layout.

## Non‑breaking and Green CI
- [ ] No breaking API changes (unless covered by an approved ADR)
- [ ] All builds/tests/linters pass (frontend and backend/BFF)
- [ ] No unresolved imports; aliases (TS) or Python paths updated

## Hexagonal Boundaries (Backend/BFF)
- [ ] Controllers (api/*) are thin and call application use-cases only
- [ ] Application layer defines ports; no framework imports in domain/application
- [ ] Adapters implement ports; no adapter/infrastructure imports from domain/application
- [ ] Cross-module interactions are explicit via ports/public APIs (no deep imports)

## Frontend Principles
- [ ] UI components are “dumb” (presentational): props in, callbacks out; minimal local UI state
- [ ] No data-fetching or global state in components; logic lives in hooks/containers/services
- [ ] Imports use path aliases (@components, @features, @utils, @services) where applicable
- [ ] Unit tests co-located with components; broader tests under tests/integration or tests/e2e

## Structure & Naming
- [ ] Feature/module directories exist with the agreed subfolders (domain, application, adapters, infrastructure)
- [ ] Directories use kebab-case; components are PascalCase; functions/vars camelCase
- [ ] Barrel exports (index.ts) expose stable public surface; no deep imports bypassing barrels

## Documentation & Governance
- [ ] Related docs updated (module README, Architecture.md links)
- [ ] References to ADR-001/002/003 and RFC included in PR description
- [ ] Migration notes and any temporary re-exports/deprecations documented

## Risk & Rollback
- [ ] Small, reversible changes; sample diffs or move plan included
- [ ] If feature toggles or temporary aliases are used, note cleanup follow-ups

