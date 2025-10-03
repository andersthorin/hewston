# Target Architecture & Conventions (Hexagonal + Modular)

Date: 2025-10-03

## 1. Goals
- Align repository with Hexagonal (Ports & Adapters) within clear feature modules.
- Improve cohesion and discoverability via component-/feature-centric layout.
- Enable test colocation; separate cross-cutting integration/e2e tests.
- Provide naming, suffix, exports, and alias conventions to enforce boundaries.

## 2. Target Repository Structure (high-level)

```
backend/
  modules/
    backtests/
      domain/
      application/
        ports/
      adapters/
      infrastructure/
    catalog/
    market-data/
  app/               # FastAPI app wiring (kept minimal; infra composition)
  api/               # Routers delegate to modules' application layer
  shared/            # (optional) ONLY stable cross-module abstractions

bff/
  modules/
    backtests/
      domain/
      application/
        ports/
      adapters/      # outbound httpx/websocket
      infrastructure/
  app/
  api/

frontend/
  src/
    components/
      runs-table/
        RunsTable.tsx
        RunsTable.test.tsx
        index.ts
        styles.css
    features/
      backtests/
        BacktestsList.tsx
        BacktestsList.test.tsx
        index.ts
    tests/           # optional feature-level integration
  tests/
    e2e/
    integration/

tests/
  e2e/
  integration/
```

Notes:
- API controllers live in api/ but are thin; they call application use-cases in modules.
- Infrastructure hosts DI/composition; domain and application have no framework imports.

## 3. Hexagonal Rules
- Domain: pure entities/value-objects/domain services; no framework deps.
- Application: use-cases; defines ports (interfaces). Depends on domain only.
- Adapters: implement inbound/outbound ports; talk to frameworks, DBs, external APIs.
- Infrastructure: composition root (wiring), config, server setup.
- Dependency direction: adapters/infrastructure -> application -> domain.

## 4. Naming & File Suffix Conventions
- Directories: kebab-case (e.g., runs-table, market-data)
- React components: PascalCase; functions/vars: camelCase
- Tests: *.test.ts(x) for unit; *.spec.ts(x) optional for broader integration
- Stories (optional): *.stories.tsx
- Barrels: index.ts exports module/component public API

## 5. Frontend TypeScript Aliases (proposal)
Add to frontend/tsconfig.app.json:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@components/*": ["src/components/*"],
      "@features/*": ["src/features/*"],
      "@utils/*": ["src/utils/*"],
      "@services/*": ["src/services/*"]
    }
  }
}
```

Import example (before/after):

```diff
- import RunsTable from "../components/RunsTable"
+ import { RunsTable } from "@components/runs-table"
```

## 6. Module Boundary Rules (enforcement guidance)
- Frontend:
  - Disallow cross-feature imports except via each feature's index.ts (public API).
  - Allow components to import sibling files; prefer relative within component dir.
  - Consider eslint-plugin-boundaries or custom ESLint rules (ADR to follow).
- Backend/BFF:
  - No imports from adapters/infrastructure into domain/application.
  - Cross-module references must go through explicit application ports.
  - Keep shared/ extremely small; prefer duplication over premature generalization.

## 7. Controllers and Use-Case Mapping
- HTTP route -> controller (api/*) -> application use case -> domain
- Outbound calls (DB/HTTP/WS) happen via application ports implemented by adapters.

## 8. DTOs and Validation
- Keep transport/request/response models in adapters/controllers.
- Domain models should express invariants; where Pydantic is used, keep validation separate from transport schemas.

## 9. Example Backend Module Map (Backtests)

```
backend/modules/backtests/
  domain/
    entities.py
    value_objects.py
    services.py
  application/
    use_cases/
      list_backtests.py
      get_backtest.py
    ports/
      catalog_repo.py
      backtest_runner.py
  adapters/
    sqlite_catalog_repo.py
    nautilus_runner.py
    http/controllers.py  # thin; maps to FastAPI router
  infrastructure/
    wiring.py            # DI/container setup for this module
```

## 10. Example BFF Module Map (Backtests)

```
bff/modules/backtests/
  application/
    use_cases/
      get_chart_data.py
    ports/
      backend_gateway.py
  adapters/
    http/backend_gateway_httpx.py
    http/controllers.py
  domain/
  infrastructure/
```

## 11. Test Layout
- Unit tests: co-located with the subject (Component.test.tsx, *.test.py).
- Integration tests: tests/integration/<area>/
- E2E: tests/e2e (or app-specific e2e per package).

## 12. Export Patterns
- index.ts barrels expose only stable, public surface.
- Avoid deep imports into subfolders from outside the component/feature.

## 13. Documentation
- Repo-level Architecture.md references this document.
- Each module has a README.md describing its public API, ports, and adapters.



## 14. UI Component Principles
- Prefer "dumb" (presentational) UI components:
  - Accept data and callbacks via typed props; minimal local UI state only.
  - No direct data-fetching, global state, or cross-feature knowledge within components.
  - Externalize logic to hooks (e.g., useXyz), containers, or service modules; keep components reusable and testable.
