<!-- Powered by BMAD™ Core -->

# Repository‑wide Code Quality Gates & CI Hardening — Brownfield Enhancement

## Epic Title

Repository‑wide Code Quality Gates & CI Hardening — Brownfield Enhancement

## Epic Goal

Establish consistent, enforceable code‑quality gates across backend, BFF, and frontend using proven off‑the‑shelf tooling and GitHub Actions. Outcomes: readable/maintainable code, predictable structure and naming, guardrails for refactors, and fast feedback in CI.

## Epic Description

**Existing System Context:**
- Current relevant functionality: Full‑stack repo with Python backend (FastAPI), Python BFF (FastAPI), and a React/Vite/TypeScript frontend. Extensive unit/integration tests exist in `backend/tests`, `bff/tests`, and `frontend/src/**/__tests__`.
- Technology stack: Python 3.11+, FastAPI, PyTest; Frontend: Vite + React 19 + TS ~5.8, ESLint flat config, Vitest.
- Integration points: Frontend → BFF (REST/WebSocket); BFF → Backend (REST/WebSocket); shared contracts (types/schemas, streaming).

**Enhancement Details:**
- What’s being added/changed:
  - Introduce/standardize quality tools: Python: Ruff (lint/imports), Black (format), MyPy (typing), PyTest + Coverage, Bandit (security), pip‑audit (vulns). Frontend: ESLint (typescript‑eslint + react‑hooks), Prettier (format), TypeScript strict type‑check, Vitest coverage, optional Playwright smoke.
  - Add two GitHub Actions workflows: `python-ci.yml` (backend + bff matrix) and tighten `frontend-ci.yml` (full lint/type/format checks, coverage thresholds, build). Cache dependencies; fail on violations.
  - Add minimal config files where missing (ruff/black/mypy/prettier/eslint coverage), plus pre‑commit hooks to shift left locally.
- How it integrates:
  - Non‑invasive: no API changes. Tools run locally (opt‑in via pre‑commit) and on PR via CI. Code annotations via GitHub summary and (optionally) SARIF.
- Success criteria:
  - CI blocks merges on failing lint/format/type/test/coverage/security gates; developers have single‑command scripts to run the same locally.

## Stories (1–3)
1. Python services quality gates (backend + bff)
   - Add shared configs: `ruff.toml` (rulesets incl. pycodestyle/pyflakes, isort), Black (via `pyproject.toml` or `black.toml`), `mypy.ini` with strict‑ish settings, `pytest.ini` with coverage paths, Bandit config.
   - Add GitHub Action `python-ci.yml`: matrix over {backend,bff} and Python {3.11,3.12}; steps: install, ruff lint, black --check, mypy, pytest with coverage>=85%, bandit, pip‑audit. Cache with `setup-python`/pip cache or uv.
   - Add `pre-commit` with ruff/black/mypy/pytest -q on changed files.

2. Frontend quality gates (Vite/TS/React)
   - Ensure ESLint flat config covers app and services/util dirs; add `eslint-config-prettier` and Prettier dependency/config; keep `typescript-eslint` recommended.
   - Expand CI: run `eslint .`, `prettier --check .`, `tsc --noEmit`, `vitest --coverage` with threshold (e.g., statements>=80%). Build `vite build` to verify.
   - Optional: basic Playwright smoke in CI (launch dev build, one e2e smoke) gated but non‑blocking initially.

3. Developer ergonomics & documentation
   - Add npm/pip scripts for one‑shot local checks, document in CONTRIBUTING.md.
   - Add shared naming/folder guidance: PEP8 for Python; TypeScript: PascalCase components, camelCase vars, kebab‑case filenames except React components; colocated tests in `__tests__` and `*.test.ts(x)`; clear module boundaries per existing folders.
   - Ensure `.gitignore` excludes build artifacts and `node_modules/` (to avoid repo bloat) and align with current repo conventions.

## Compatibility Requirements
- [x] Existing APIs remain unchanged
- [x] Database schema changes are backward compatible (N/A — no schema changes)
- [x] UI changes follow existing patterns (N/A — CI only)
- [x] Performance impact is minimal (CI only; runtime unaffected)

## Risk Mitigation
- Primary Risk: CI instability or flakiness increases PR cycle time.
- Mitigation: Start with advisory thresholds (warn) in first PR, then enforce; cache deps; run fast linters (Ruff) before heavier steps; isolate flaky tests.
- Rollback Plan: Revert workflow file(s) or lower thresholds in a single PR; configs are additive and safe to remove if needed.

## Definition of Done
- [x] Python and frontend CI workflows created/updated and passing on main
- [x] Lint/format/type/test/security gates enforced with clear thresholds
- [x] Local dev scripts and pre‑commit hooks available and documented
- [x] Repo docs updated with naming/folder structure guidelines
- [x] No regressions in existing tests; builds remain green

## Validation Checklist
**Scope Validation**
- [x] Epic can be completed in 1–3 stories maximum
- [x] No architectural documentation is required
- [x] Enhancement follows existing patterns
- [x] Integration complexity is manageable

**Risk Assessment**
- [x] Risk to existing system is low
- [x] Rollback plan is feasible
- [x] Testing approach covers existing functionality
- [x] Team has sufficient knowledge of integration points

**Completeness Check**
- [x] Epic goal is clear and achievable
- [x] Stories are properly scoped
- [x] Success criteria are measurable
- [x] Dependencies are identified

## Story Manager Handoff
"Please develop detailed user stories for this brownfield epic. Key considerations:
- This is an enhancement to an existing system running: Python FastAPI services (backend, BFF) and a React/Vite/TypeScript frontend
- Integration points: Frontend↔BFF (REST/WebSocket); BFF↔Backend (REST/WebSocket)
- Existing patterns to follow: current folder/module structure; colocated tests; ESLint flat config in frontend; PyTest test layout in services
- Critical compatibility requirements: no API changes; CI‑only; coverage thresholds must be adjustable per module
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering enforceable quality gates across the repo."

