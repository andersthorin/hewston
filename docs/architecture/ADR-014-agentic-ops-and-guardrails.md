# ADR-014 — Agentic Ops and Guardrails (Epic 21)

Status: Accepted
Date: 2025-10-10
Related Epics: PRD Epic 21; Stories: 21.1–21.7
References: ADR-009 (Agentic API), ADR-012 (Risk policies)

## Context
Agentic Mode must be safe-by-default in shared/dev environments with predictable costs and operator controls.

## Decision
- Introduce a centralized Ops policy for Agentic runs:
  - Global kill-switch: `AGENTIC_MODE_ENABLED` (enforced at endpoints)
  - Backpressure/quotas (per-user, per-minute caps; 429 on exceed)
  - Budget hints and size limits propagated into plan execution
  - Structured logs and minimal counters for auditing (propose, start, duplicate, error)
- Record user consent and policy snapshot into run manifest.
- Provide observability hooks (metrics, logs) to the existing metrics pipeline.

## Consequences
- Operators can disable Agentic Mode instantly and review usage.
- Predictable cost/risk envelopes for evaluation runs.

## Implementation Notes
- FastAPI deps/middleware to enforce quotas (phase 2); initial phase includes kill-switch and logging only.
- Emit structured logs with event types: agentic.propose, agentic.start, agentic.denied.

## Testing
- Unit tests for disabled mode (403) and logging presence.
- Integration tests for backpressure once quotas are implemented.

## Alternatives
- Env-only controls without logs (rejected; insufficient auditability).

## References
- docs/prd/epic-21-agentic-ops-and-guardrails.md

