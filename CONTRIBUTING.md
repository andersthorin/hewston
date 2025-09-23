# Contributing to Hewston

Thank you for contributing! This guide ensures consistent, high‑quality changes.

## Before you start
- Read: docs/prd.md and docs/architecture.md
- Skim: docs/architecture/tech-stack.md, source-tree.md, coding-standards.md
- Baselines: docs/prd/features/00-baselines.md
- Contracts: docs/api/openapi.yaml, docs/api/ws-protocol.md, docs/api/error-codes.md
- QA: docs/qa/story-to-qa-mapping.md; docs/qa/performance-test-plan.md

## Branches & Commits
- Use Conventional Commits: feat:, fix:, docs:, refactor:, test:, chore:
- Reference Story ID (e.g., S2.3) and QA IDs in PR description

## PR Checklist (must pass)
- [ ] Lint/format clean (Makefile targets: lint, format)
- [ ] Tests pass (Makefile target: test)
- [ ] ACs satisfied; Story ID referenced; QA mapping updated if needed
- [ ] API/WS docs updated if endpoints/protocol changed
- [ ] Determinism/perf budgets met (where relevant)
- [ ] Logs/counters aligned with coding standards (where relevant)

## Running locally
- Env: copy .env.example to .env and export
- DB schema: `make db-apply`
- Dataset: `make data SYMBOL=AAPL YEAR=2023`
- Backtest: `make backtest ...`
- Servers: `make start`

## Story standards
- Apply DoR/DoD from docs/process/story-standards.md
- Include Dependencies and References in story files

## Security & Secrets
- Never commit real secrets; see docs/security/secrets-and-env.md

## Questions
Open an issue or start a discussion. Document decisions when they affect PRD/Architecture.

