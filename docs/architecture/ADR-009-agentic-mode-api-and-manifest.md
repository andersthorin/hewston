# ADR-009 — Agentic Mode API and Manifest Integration (Epic 16)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 16, Process epic-16-plan; Stories: 16.1–16.10
Supersedes/References: ADR-004 (Agent orchestration), ADR-008 (Plan schema & manifest versioning)

## Context
We are introducing an Agentic Mode that proposes and executes backtest plans. We need:
- Explicit API contracts for propose/start
- A kill-switch for safe rollout
- Minimal manifest persistence at enqueue-time, later merged at finalize-time
- Idempotency by canonical input hash and optional idempotency key
- Consent capture (headers) for auditable usage

## Decision
- Add FastAPI routes:
  - POST /agentic/propose_plan -> returns PlanV1
  - POST /agentic/start -> enqueues run(s) from provided plan or embedded body
- Gate both routes with AGENTIC_MODE_ENABLED env variable; default enabled for dev.
- Capture optional consent headers `X-Agentic-Consent-By` and `X-Agentic-Consent-At` and store under manifest.agentic_consent.
- At create time, persist a minimal manifest (run-manifest.json) including plan and plan hash; at job completion, merge minimal manifest with final fields (status, metrics, bar_interval_minutes, etc.).
- Compute canonical input hash over deterministic subset of inputs, store in DB and use as idempotency key alongside request header idempotency.
- Extend create_backtest_service to accept { agentic_plan, agentic_plan_hash, consent }.

## Consequences
- Safer rollout with a single env flag to disable Agentic Mode.
- Reproducibility: manifests consistently contain plan and hash; minimal manifest present even if job fails early.
- Backward compatibility: existing manual mode unaffected; idempotency unchanged for non-agentic runs.
- Slightly larger manifests; negligible performance impact.

## Implementation Notes
- backend/api/routes/agentic.py: env gate + consent capture + JSON error handling.
- backend/services/backtests.py: carry plan + consent into minimal manifest; compute plan hash if missing.
- backend/jobs/run_backtest.py: merge final manifest with minimal manifest to preserve agentic fields.

## Testing
- Unit/route tests for 200/400/403 paths; idempotency duplicate behavior; consent headers presence.
- Manifest schema spot-checks.

## Alternatives Considered
- Storing plan only in DB artifacts instead of manifest (rejected: operators use manifest for audits).
- Forcing plan IDs only (rejected; supporting inline plan simplifies UX/testing).

## References
- docs/prd/epic-16-agentic-backtest-orchestrator.md
- docs/architecture/ADR-004-agent-orchestration-framework.md
- docs/architecture/ADR-008-plan-schema-and-manifest-versioning.md

