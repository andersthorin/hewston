# Epic 1 — Backend Skeleton

Goal
- Establish the FastAPI application skeleton with health endpoint, WebSocket echo, route stubs, and DI wiring as the foundation for subsequent epics.

Why (Value)
- Validates runtime, structure, and transport choices early (REST + WebSocket primary, SSE fallback). Unblocks catalog, jobs, and playback work.

Scope (In)
- FastAPI app factory (app/main.py)
- /healthz route (liveness)
- WebSocket endpoint at /backtests/{id}/ws that accepts connections and echoes ctrl messages
- Backtests route module scaffolding (POST/GET stubs only)
- Lightweight DI wiring for ports/adapters (interfaces only)

Out of Scope
- Business logic (catalog, ingest, backtests execution)
- SSE fallback implementation

Deliverables
- Backend source tree created per Architecture
- Working /healthz (200 OK JSON)
- WS endpoint that upgrades and echoes
- Route stubs for /backtests

Acceptance Criteria
- make start-backend serves /healthz with {"status":"ok"}
- ws://localhost:8000/backtests/{id}/ws accepts a connection and echoes `{ "t":"ctrl", ... }`
- Code layout matches Source Tree & Module Boundaries

Dependencies
- None (first epic)

Risks & Mitigations
- Event loop blocking → Keep CPU-bound work out of handlers; echo only
- Over-scaffolding → Keep minimal; defer features to later epics

Definition of Done
- All acceptance criteria met; code structure matches docs; no long-running tasks inside request handlers

References
- Architecture: Tech Stack; API Contracts (REST + WebSocket); Source Tree and Module Boundaries; Non-Functional Requirements

