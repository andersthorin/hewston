# ADR-003: Backend/BFF Module Extraction Strategy (Ports & Adapters)

Date: 2025-10-03
Status: Proposed
Decision Type: Backend/Services

## Context
The backend already has domain/ports/adapters directories but lacks per-feature modularization and keeps cross-cutting services/utils. The BFF structures app/api/services but lacks explicit domain/application/ports/adapters. Coupling exists (e.g., bff uses backend.app.logging_setup).

## Decision
Adopt per-feature modules for backend and BFF:

- Structure: modules/<feature>/{domain, application (with ports), adapters, infrastructure}
- Application layer defines use-cases and ports (protocols/interfaces)
- Adapters implement ports (DB/HTTP/external libs) and inbound controllers
- Infrastructure composes modules and frameworks (DI, FastAPI wiring, config)
- Avoid cross-service coupling (BFF does not import backend internals)

## Rationale
- Enables strict dependency direction toward domain.
- Improves isolation and testability of use-cases and adapters.
- Limits shared/ to stable primitives only.

## Consequences
- Short-term overhead to move files and update imports.
- Potential duplication until shared utilities are re-homed or eliminated.

## Alternatives Considered
- Keep global ports/adapters: rejected due to scaling and coupling issues.

## Implementation Notes (Pilot)
- Backend/backtests: move ports/backtest_runner.py and adapters/nautilus.py into modules/backtests. Introduce application/use_cases and infrastructure/wiring.
- BFF/backtests: create outbound port (backend_gateway.py) and httpx adapter; move route handlers into adapters/http/controllers.py.
- Logging: BFF owns its logging setup; remove dependency on backend.app.logging_setup.

