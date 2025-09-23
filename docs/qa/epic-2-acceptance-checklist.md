# Epic 2 — Catalog Adapter and Models: Acceptance Test Checklist
Epic ID: E2



Preconditions
- `make db-apply` completed; data/catalog.sqlite created
- Backend skeleton from Epic 1 running

Test Cases
1) GET /backtests empty list (AC)
   - Step: GET http://127.0.0.1:8000/backtests
   - Verify: 200; body { items: [], total: 0, limit, offset }

2) GET /backtests/{id} 404 (AC)
   - Step: GET /backtests/does-not-exist
   - Verify: 404; { error: { code: "RUN_NOT_FOUND", message } }

3) Model alignments
   - Inspect adapter serialization maps to Pydantic models: Dataset, Run, RunMetrics
   - Verify shape fields match docs/architecture.md Data Models

4) Performance & logging (sanity)
   - Verify: Requests complete <200 ms locally; logs include request_id

Pass/Fail Criteria
- Endpoints return correct shapes; 404 behaves correctly; no schema mismatches

Artifacts
- Optional: SQL dump of sqlite .schema; sample responses saved as JSON

