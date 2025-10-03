# ADR-001: Repository Directory Strategy & Hexagonal Boundaries

Date: 2025-10-03
Status: Proposed
Decision Type: Architecture/Organizational

## Context
The repository contains three applications (backend, bff, frontend). The backend currently uses folders named domain/ports/adapters, but feature boundaries are not encapsulated. The BFF mixes routing and orchestration. The frontend is layer-centric rather than component/feature-centric with no path aliases.

## Decision
Adopt a feature-by-feature modular structure with Hexagonal (Ports & Adapters) layering across backend and BFF, and component-/feature-centric structure on the frontend.

- Backend and BFF:
  - Create modules/<feature> with subfolders: domain, application (with ports), adapters, infrastructure.
  - Keep framework wiring/configuration in infrastructure and app/.
  - API controllers are thin and call application use-cases; no domain/application imports from adapters.
- Frontend:
  - Use component- and feature-centric directories under src/.
  - Co-locate unit tests with the subject; keep multi-module/e2e tests under tests/.
  - UI components should be “dumb”: presentation-only, with state/data-fetching and orchestration externalized in hooks/containers/services. Expose small, typed props; no cross-feature knowledge.

## Rationale
- Improves cohesion and discoverability; reduces coupling and accidental cross-module imports.
- Aligns dependency direction toward the domain, enabling testing and substitution of adapters.
- Simplifies onboarding and PR review by scoping changes per module/component.

## Consequences
- Short term: folder moves and import updates; temporary duplication while extracting modules.
- Medium term: clearer boundaries; easier to test; lower risk of regressions.
- Requires discipline to keep shared/ small and stable.

## Alternatives Considered
- Keep layer-centric structure (services/utils): rejected due to coupling and scaling risks.
- Single shared “core” package: acceptable only for truly stable abstractions; avoided initially.

## Implementation Notes (Pilot)
- Backend: Extract backtests module; define application ports and move adapters accordingly.
- BFF: Mirror backtests module; outbound port to backend via httpx.
- Frontend: Restructure RunsTable component; co-locate tests; add barrel export.

