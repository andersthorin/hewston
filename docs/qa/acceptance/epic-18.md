# QA Acceptance — Epic 18 Equities Universe Management

Scope
- UniverseV1 manifest and inclusion rules
- Coverage thresholds applied in propose_plan
- Catalog alignment (dataset_id/instrument_id defaults)

Test Matrix
1) Universe manifest
- Valid manifest loads and validates (symbols[], as_of present)
- Invalid manifest (missing symbols) → validation error

2) Coverage filtering
- propose_plan prunes symbols below threshold coverage
- With adequate coverage, symbols included and run windows match PRD rules

3) Catalog alignment
- Selected symbols map to default instrument_id (e.g., AAPL.XNAS)
- Missing mapping → plan marks symbol with reason code (SKIPPED_NO_INSTRUMENT)

4) Admin refresh
- Admin CLI/API refresh writes a versioned UniverseV1 and updates catalog link

Artifacts
- UniverseV1 manifest snapshot; logs of propose_plan coverage decisions
- PlanV1 JSON conforms to docs/api/schemas

