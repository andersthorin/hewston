# Epic 7 — Hardening & NFRs: Acceptance Test Checklist
Epic ID: E7



Preconditions
- Core features complete (Epics 1–6)

Test Cases
1) Logging fields (AC)
   - Exercise: Run ingest/derive/backtest/playback flows
   - Verify: JSON logs include request_id, run_id, idempotency_key where applicable

2) Minimal metrics (AC)
   - Verify presence of counters/timers: ingest/derive/backtest durations; frames/sec produced/sent/dropped; WS disconnects
   - Accept log-based metrics for MVP

3) Retention/pruning (AC)
   - Step: Create >N runs
   - Run: retention tool/command (dry-run then apply)
   - Verify: Old artifacts removed; catalog remains consistent (no dangling rows/paths)

4) Performance budgets (AC)
   - REST latency: median ≤50 ms; P95 ≤200 ms (local)
   - WS jitter: median ≤30 ms; P95 ≤80 ms; playback ~30 FPS
   - Storage: symbol-year ≤250 MB; per-run ≤50 MB

5) Error handling & status transitions (AC)
   - Inject failure in job to simulate ERROR
   - Verify: Catalog status transitions QUEUED→RUNNING→DONE/ERROR; partial artifacts flagged

Security/Binding
- Verify default bind 127.0.0.1; permissive CORS only for local dev; no auth by default

Pass/Fail Criteria
- All NFR targets met (or variances documented with mitigation plan); operability tools work without data loss

Artifacts
- NFR validation report; retention logs; sample structured logs

