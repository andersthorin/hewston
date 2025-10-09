# QA Acceptance — Epic 16 Agentic Backtest Orchestrator

Scope
- UI: Agentic Mode toggle, Plan Preview, Start
- API: POST /agentic/propose_plan, POST /agentic/start, GET /runs/{id}/manifest

Test Matrix
1) Toggle behavior
- OFF: manual mode visible and functional
- ON: only date range required; manual fields hidden

2) propose_plan
- Valid dates → 200 with PlanV1 and guardrail checks
- Invalid date format → 400
- Backpressure simulated → 429

3) start_agentic_run
- With plan_id (fresh) → 200, run_ids[] returned, ManifestV1 persisted
- With plan payload (fresh) → 200, same as above
- Duplicate plan_hash → 202 or 200 with note; no new jobs; UI shows duplicate copy
- Guardrail failure → 400 with reason codes (e.g., COVERAGE_LOW)
- Backpressure → 429

4) Manifest
- GET returns schema-valid ManifestV1 with embedded PlanV1, code_hash, seeds, timeline

5) Feature flag and consent
- When flag OFF: Agentic toggle hidden; endpoints guarded
- First-time consent modal appears; consent recorded and respected thereafter

Artifacts
- Validate JSON against docs/api/schemas
- Snapshots of duplicate-plan UX and error messages

