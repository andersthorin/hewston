# ADR-011 — Equities Universe Management (Epic 18)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 18; Stories: 18.1–18.6

## Context
Agentic planning and multi-strategy backtests require a manageable equities universe. We need a single source of truth for: symbols, venues, inclusion rules, and coverage windows backed by the warehouse/catalog.

## Decision
- Introduce a Universe manifest (UniverseV1) with fields: source, as_of, symbols[], inclusion rules, default instrument_id per symbol.
- Persist universe metadata in catalog (dataset table or a new table) and/or as a versioned manifest in data/universe/.
- Expose an admin-only CLI/API to refresh universe from external sources (e.g., static list, CSV, metadata service).
- Agentic propose_plan consults UniverseV1 to filter symbols for which coverage meets minimum thresholds.

## Consequences
- Deterministic symbol selection and repeatability across runs.
- Clear boundary between data availability (warehouse) and plan selection logic.

## Implementation Notes
- Backend: service function to read/validate UniverseV1; helper to compute coverage per symbol.
- Align with catalog adapter to surface default instrument_id (e.g., AAPL.XNAS).
- Version and timestamp universe manifests for audits.

## Testing
- Unit tests for inclusion rule evaluation and coverage thresholds.
- Integration test: propose_plan prunes symbols without adequate coverage.

## Alternatives
- Selecting symbols ad-hoc at plan time (rejected; too flaky, non-reproducible).

## References
- docs/prd/epic-18-equities-universe-management.md
- docs/architecture/nautilus-integration-architecture.md

