# Epic 7 — Hardening & NFRs

Goal
- Meet defined non-functional requirements, improve operability, and add retention controls.

Why (Value)
- Ensures reliability, performance, and maintainability before expanding scope.

Scope (In)
- Logging: JSON logs with request_id/run_id/idempotency_key
- Metrics: durations (ingest/derive/backtest), frames/sec produced/sent/dropped, WS disconnects
- Retention: configurable pruning of old runs/artifacts
- Performance validation against budgets (latency, memory, FPS)
- Error handling and status transitions in catalog

Out of Scope
- New product features; strategy expansion

Deliverables
- Logging fields present across API/jobs
- Minimal metrics counters exposed (even if just logs for MVP)
- Retention tool/command implemented
- NFR validation report

Acceptance Criteria
- Meets latency/storage/FPS targets from Architecture NFRs in local tests
- Logs include run_id and counters; catalog accurately reflects statuses
- Retention removes old artifacts without corrupting catalog

Dependencies
- Epics 1–6

Risks & Mitigations
- Over-engineering metrics 3 Keep minimal; rely on logs initially
- Data loss during pruning 3 dry-run mode and targeted retention

Definition of Done
- NFRs met or variances documented with mitigation plan; operability tools in place

References
- Architecture: Non-Functional Requirements and Performance Budgets; Operability & Observability

