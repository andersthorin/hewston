# Architecture Review Report

Date: 2025-10-03
Scope: Read-only audit of repository structure, frameworks, tests, and architectural boundaries; assess alignment with Hexagonal (Ports & Adapters) and modular architecture.

## 1. Current-State Inventory

### 1.1 Repository shape
- backend/ (Python, FastAPI)
- bff/ (Python, FastAPI)
- frontend/ (React + Vite + TypeScript)
- tests/ (Python tests; e2e/integration not clearly separated)
- docs/ (existing project documentation)

### 1.2 Backend (Python)
- Frameworks: FastAPI 0.115.x, uvicorn 0.30.x, structlog; pytest
- Structure observed:
  - backend/app: FastAPI app factory, CORS, middleware
  - backend/api/routes: REST routers (health, backtests, bars)
  - backend/domain: pydantic models and types (entities/DTOs)
  - backend/ports: interfaces (backtest_runner, catalog, market_data)
  - backend/adapters: implementations (sqlite_catalog, nautilus)
  - backend/services, backend/strategies, backend/utils, backend/data, backend/jobs (cross-cutting)
- Notes: Uses canonical /api/v1 route prefix. Domain uses Pydantic (acceptable if domain remains framework-agnostic in behavior).

### 1.3 BFF (Python)
- Frameworks: FastAPI, httpx, websockets, structlog, pytest-asyncio
- Structure observed:
  - bff/app: app factory, config, dependencies, middleware
  - bff/api: endpoints (proxy, chart_data, backtests, websocket, health)
  - bff/models, bff/services (service helpers)
- Notes: Imports backend.app.logging_setup (service coupling). Clear separation of app vs API, but no explicit domain/application/ports structure yet.

### 1.4 Frontend (React + Vite)
- Tooling: Vite 7, TS ~5.8, Vitest 3, ESLint 9, Testing Library, Tailwind 4 plugin
- Structure observed: src/{components,containers,hooks,services,store,utils,views,schemas,types,workers}
- Tests: Mixed colocation (e.g., RunsTable.test.tsx) and centralized folders (__tests__/integration, performance). No TS path aliases configured.
- Dev server proxy to BFF for /api/v1; direct proxy to backend for some paths.

### 1.5 Tests
- Backend: tests/backend/... (pytest) covering REST, WS behavior, utils
- BFF: bff/tests present
- Frontend: unit/integration tests within src; happy-dom environment
- Top-level: a few experimental WebSocket test scripts (test_simple_websocket.py etc.)

## 2. Observed Module Boundaries & Hexagonal Alignment

### 2.1 Backend
- Positives: Directories named domain/ports/adapters; API and app wiring are separated.
- Gaps:
  - Feature boundaries not encapsulated; cross-cutting dirs (services, utils, strategies) may be shared implicitly across features.
  - Ports are global (backend/ports) rather than per-feature module.
  - Domain uses Pydantic models; accept as domain DTOs, but keep domain rules independent of FastAPI.

### 2.2 BFF
- Positives: Clear app factory; routers organized; outbound communication via httpx/websockets.
- Gaps:
  - No explicit domain/application/ports/adapters split; controller logic likely mixes with orchestration.
  - Coupling to backend internals for logging setup.

### 2.3 Frontend
- Positives: Good testing setup; clear separation of concerns across folders.
- Gaps:
  - Layer-centric structure rather than component/feature-centric; tests not consistently co-located per component.
  - No TS path aliases → deeper relative imports; weak boundary enforcement.

## 3. Coupling Hotspots and Risks
- backend.utils/services: potential magnets for cross-feature coupling.
- bff depending on backend.app.logging_setup: cross-service coupling.
- Frontend services/utils imported broadly; lack of alias/boundary rules.
- Risk of circular deps increases with shared utility directories (no specific cycle found in quick scan).

## 4. Anti-Patterns / Deviations
- Global ports/adapters instead of per-feature modules.
- Mixing validation/transport types with domain invariants (pydantic in domain) if not carefully contained.
- Unclear e2e vs integration test separation; top-level ad-hoc tests.

## 5. Maturity Score (subjective)
- Backend: Medium (naming, intent present; needs feature modularization and stricter boundaries)
- BFF: Low–Medium (needs hexagonal layering and decoupling from backend internals)
- Frontend: Low–Medium (move to component/feature-centric structure; add path aliases; enforce boundaries)

## 6. Prioritized Issues (H/M/L)
1) Introduce feature modules across backend and BFF with per-module domain/application/ports/adapters (H)
2) Add TS path aliases in frontend and import boundary rules (H)
3) Clarify test strategy: co-locate unit tests; create tests/e2e and tests/integration (M)
4) Reduce cross-cutting backend utils/services; convert to module-internal services or ports (M)
5) BFF: eliminate import from backend internals; own infra/logging (M)
6) Optionally separate domain entities from transport/validation models (L)

## 7. Recommendations (Actionable)
- Establish per-feature modules with hexagonal subfolders in backend and BFF.
- Define application ports per module; move existing adapters to module-adapter implementations.
- Frontend: adopt component-centric directories; introduce @components, @features aliases; co-locate tests.
- Create ADRs to codify directory structure, boundaries, and path aliases.
- Introduce lightweight boundary checks in CI once approved (no change yet).

## 8. Assumptions to Confirm
- Single repo with three apps (backend, bff, frontend).
- FastAPI for backend & BFF; React/Vite frontend.
- No immediate API breaking changes; migration will be non-breaking.

## 9. Appendix: Sample Target Structures (see Target Architecture doc for details)
- Backend: backend/modules/<feature>/{domain,application,adapters,infrastructure}
- BFF: bff/modules/<feature>/{domain,application,adapters,infrastructure}
- Frontend: src/components/<kebab>/{Component.tsx, Component.test.tsx, index.ts}

