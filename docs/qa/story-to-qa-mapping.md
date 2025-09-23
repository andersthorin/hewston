[IDs]
- Refer to docs/qa/ids.md for the canonical ID scheme.
- Use Story IDs (e.g., S2.3) and QA Test Case IDs (e.g., E4-TC-3) in commits/PRs.
- AC IDs are Sx.y-AC-n; QA IDs are Ex-TC-n, matching the numbered lists below.


# Story ↔ QA Checklist Mapping

Purpose
- Map each story’s acceptance criteria (AC) to the corresponding Epic QA checklist test cases, for traceability and test planning.
- Use alongside docs/qa/index.md and the story files in docs/stories/.

Conventions
- QA refs link to the Epic acceptance checklist files under docs/qa/…
- Test case numbers refer to the numbered items in each Epic checklist.

## Epic 1 — Backend Skeleton
- Story 1.1 — Backend skeleton: health endpoint and app wiring
  - QA: [Epic 1](./epic-1-acceptance-checklist.md) — TC1 (Health), TC3 (Structure & non-blocking)
- Story 1.2 — Backend skeleton: WebSocket echo endpoint
  - QA: [Epic 1](./epic-1-acceptance-checklist.md) — TC2 (WS echo), TC3 (Structure & non-blocking)
- Story 1.3 — Backend skeleton: Backtests routes stubs
  - QA: [Epic 1](./epic-1-acceptance-checklist.md) — TC3 (Structure), plus stub behavior validated informally until Epic 2

## Epic 2 — Catalog Adapter and Models
- Story 2.1 — Catalog models + SQLite adapter (list/get runs)
  - QA: [Epic 2](./epic-2-acceptance-checklist.md) — TC1 (GET /backtests empty), TC2 (GET /backtests/{id} 404), TC3 (Model alignments)
- Story 2.2 — List runs API (filters, pagination, ordering)
  - QA: [Epic 2](./epic-2-acceptance-checklist.md) — TC1 (List shape) extended; add filter/pagination verification (expand as needed)
- Story 2.3 — Get run API (detail by id)
  - QA: [Epic 2](./epic-2-acceptance-checklist.md) — TC2 (404), TC3 (shape alignment)

## Epic 3 — Data Ingest and Derive
- Story 3.1 — Databento ingestion CLI (DBN TRADES+TBBO)
  - QA: [Epic 3](./epic-3-acceptance-checklist.md) — TC1 (Ingest), TC2 (Filesystem), TC5 (Determinism smoke)
- Story 3.2 — Derive 1m bars + minute TBBO aggregates (Parquet)
  - QA: [Epic 3](./epic-3-acceptance-checklist.md) — TC1 (Derive), TC2 (Filesystem), TC4 (Manifest integrity), TC5 (Determinism)
- Story 3.3 — Upsert Dataset in Catalog (SQLite) with Manifest
  - QA: [Epic 3](./epic-3-acceptance-checklist.md) — TC3 (Catalog row upsert)
- Story 3.4 — Ingest rate limits and retry policy (Databento)
  - QA: [Epic 3](./epic-3-acceptance-checklist.md) — Supports TC1 (Ingest robustness); add verification of backoff/retries and idempotent writes



## Epic 4 — Backtest Runner & Artifacts
- Story 4.1 — Nautilus adapter integration (BacktestRunnerPort)
  - QA: [Epic 4](./epic-4-acceptance-checklist.md) — Contributes to TC1–TC4 (execution, artifacts, metrics); adapter smoke test not explicitly listed
- Story 4.2 — Run job + write artifacts
  - QA: [Epic 4](./epic-4-acceptance-checklist.md) — TC1 (Create run), TC2 (Completion), TC3 (Artifacts), TC4 (Metrics)
- Story 4.3 — Idempotent POST /backtests (enqueue + status)
  - QA: [Epic 4](./epic-4-acceptance-checklist.md) — TC1–TC2 (Create/Status), TC5 (Idempotency)

## Epic 5 — Playback Streaming
- Story 5.1 — Streamer service + frame decimation
  - QA: [Epic 5](./epic-5-acceptance-checklist.md) — Supports TC1 (FPS), TC3 (Dropped counter), TC5 (hb/end/err)
- Story 5.2 — WebSocket endpoint + control handling
  - QA: [Epic 5](./epic-5-acceptance-checklist.md) — TC1 (FPS), TC2 (Controls), TC3 (Backpressure), TC5 (hb/end/err)
- Story 5.3 — SSE fallback endpoint (frames)
  - QA: [Epic 5](./epic-5-acceptance-checklist.md) — TC4 (SSE fallback)


- Story 6.0 — UX artifacts: wireframes and FE component map
  - QA: [Epic 6](./epic-6-acceptance-checklist.md) — Supports TC1/TC2 by providing design artifacts; verify presence and completeness (wireframes, flows, component map)

## Epic 6 — Frontend MVP
- Story 6.1 — Runs List view (presentational UI)
  - QA: [Epic 6](./epic-6-acceptance-checklist.md) — TC1 (Runs List), TC3 (Presentational components)
- Story 6.2 — Run Detail playback view (charts + controls)
  - QA: [Epic 6](./epic-6-acceptance-checklist.md) — TC2 (Run Detail playback), TC4 (Performance sanity)
- Story 6.3 — WS hook, Worker parsing, and overlays wiring
  - QA: [Epic 6](./epic-6-acceptance-checklist.md) — Supports TC2 (playback stability), TC3 (presentational-only rule)

## Epic 7 — Hardening & NFRs
- Story 7.1 — Logging and minimal metrics (operability)

- Story 7.5 — Operability hooks: structured logs and minimal counters
  - QA: [Epic 7](./epic-7-acceptance-checklist.md) — TC1 (Logging), TC2 (Minimal metrics)

- Story 7.2 — Retention and pruning of runs/artifacts
  - QA: [Epic 7](./epic-7-acceptance-checklist.md) — TC3 (Retention/pruning)
- Story 7.3 — Performance budgets validation (latency, jitter, storage)
  - QA: [Epic 7](./epic-7-acceptance-checklist.md) — TC4 (Performance budgets)
- Story 7.4 — Error handling and catalog status transitions
  - QA: [Epic 7](./epic-7-acceptance-checklist.md) — TC5 (Error handling & transitions)

Notes
- As the system evolves, keep this mapping updated whenever stories or QA checklists change.
- Consider adding IDs to story ACs and QA test cases for automated traceability in the future.

