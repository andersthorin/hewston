# Epic 2 — Catalog Adapter and Models

Goal
- Implement catalog persistence with SQLite and Pydantic models to list/get runs; keep artifacts on filesystem paths.

Why (Value)
- Enables visibility into runs and datasets, provides the backbone for UI list/browse and later orchestration.

Scope (In)
- Pydantic models: Dataset, DatasetManifest, Run, RunManifest, RunMetrics
- SQLite adapter implementing CatalogPort using provided DDL
- GET /backtests (filters + pagination) — returns empty list on fresh DB
- GET /backtests/{id} — 404 for unknown; success shape aligned with models

Out of Scope
- Creation of runs, metrics computation, or artifact writing

Deliverables
- adapters/sqlite_catalog.py
- domain/models.py (Pydantic v2)
- services/backtests.py (list/get wired to CatalogPort)

Acceptance Criteria
- `make db-apply` creates data/catalog.sqlite with tables/views
- `GET /backtests` responds 200 with `{ items: [], total: 0, ... }` on fresh DB
- `GET /backtests/{id}` 404 when not found

Dependencies
- Epic 1 (Backend Skeleton)

Risks & Mitigations
- Schema drift  Keep DDL source-of-truth in scripts/catalog_init.sql; adapter aligns to it
- Overfetching/serialization  Use select columns and Pydantic model configs

Definition of Done
- Endpoints and adapter pass basic responses; models match Architecture Data Models

References
- Architecture: Data Models; Catalog Schema (SQLite DDL); API Contracts; Source Tree

