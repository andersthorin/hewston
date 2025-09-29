# QA Testing Reference

**Status**: v0.1 — Consolidated QA documentation for Hewston trading platform  
**Last Updated**: 2025-01-27

## Table of Contents

1. [Epic Acceptance Checklists Index](#1-epic-acceptance-checklists-index)
2. [ID Scheme & Traceability](#2-id-scheme--traceability)
3. [Story-to-QA Mapping](#3-story-to-qa-mapping)
4. [NFR Validation Framework](#4-nfr-validation-framework)
5. [Performance Testing Plan](#5-performance-testing-plan)

---

## 1. Epic Acceptance Checklists Index

Use this index to navigate the acceptance test checklists for each epic. Follow each checklist to validate MVP functionality and NFRs.

### Epic Checklists
- [Epic 1 — Backend Skeleton](./qa/epic-1-acceptance-checklist.md)
- [Epic 2 — Catalog Adapter and Models](./qa/epic-2-acceptance-checklist.md)
- [Epic 3 — Data Ingest and Derive](./qa/epic-3-acceptance-checklist.md)
- [Epic 4 — Backtest Runner & Artifacts](./qa/epic-4-acceptance-checklist.md)
- [Epic 5 — Playback Streaming](./qa/epic-5-acceptance-checklist.md)
- [Epic 6 — Frontend MVP](./qa/epic-6-acceptance-checklist.md)
- [Epic 7 — Hardening & NFRs](./qa/epic-7-acceptance-checklist.md)

### How to Use
- Before testing, ensure prerequisites in each checklist are met
- Prefer local verification first; keep logs and sample outputs as artifacts
- Record pass/fail results and issues directly in the checklist files or your tracking system

### Detailed Test Gates
For granular test specifications, see individual gate files in [`docs/qa/gates/`](./qa/gates/) directory.

---

## 2. ID Scheme & Traceability

**Purpose**: Provide stable identifiers for traceability between stories and QA checklists without changing every file.

### ID Scheme
- **Epic IDs**: E{n} where n ∈ [1..7]
- **Story IDs**: S{epicNum}.{storyNum} (e.g., S2.3)
- **Story Acceptance Criteria IDs**: S{epic}.{story}-AC-{n} where n is the ordinal number in that story's Acceptance Criteria list
- **QA Test Case IDs**: E{epic}-TC-{n} where n is the ordinal number in the corresponding Epic acceptance checklist

### Examples
- Story "docs/stories/2.3.story.md" → Story ID: S2.3; its second AC → S2.3-AC-2
- QA checklist "docs/qa/epic-4-acceptance-checklist.md" → Epic ID: E4; its third test case → E4-TC-3

### Epic Mapping
| Epic ID | Epic Name | Checklist File |
|---------|-----------|----------------|
| E1 | Backend Skeleton | epic-1-acceptance-checklist.md |
| E2 | Catalog Adapter and Models | epic-2-acceptance-checklist.md |
| E3 | Data Ingest and Derive | epic-3-acceptance-checklist.md |
| E4 | Backtest Runner & Artifacts | epic-4-acceptance-checklist.md |
| E5 | Playback Streaming | epic-5-acceptance-checklist.md |
| E6 | Frontend MVP | epic-6-acceptance-checklist.md |
| E7 | Hardening & NFRs | epic-7-acceptance-checklist.md |

### Story Mapping
| Story ID | Story Name | Story File |
|----------|------------|------------|
| S1.1 | Backend skeleton: health endpoint and app wiring | 1.1.story.md |
| S1.2 | Backend skeleton: WebSocket echo endpoint | 1.2.story.md |
| S1.3 | Backend skeleton: Backtests routes stubs | 1.3.story.md |
| S2.1 | Catalog models + SQLite adapter (list/get runs) | 2.1.story.md |
| S2.2 | List runs API (filters, pagination, ordering) | 2.2.story.md |
| S2.3 | Get run API (detail by id) | 2.3.story.md |
| S3.1 | Databento ingestion CLI (DBN TRADES+TBBO) | 3.1.story.md |
| S3.2 | Derive 1m bars + minute TBBO aggregates (Parquet) | 3.2.story.md |
| S3.3 | Upsert Dataset in Catalog (SQLite) with Manifest | 3.3.story.md |
| S4.1 | Nautilus adapter integration (BacktestRunnerPort) | 4.1.story.md |
| S4.2 | Run job + write artifacts | 4.2.story.md |
| S4.3 | Idempotent POST /backtests (enqueue + status) | 4.3.story.md |
| S5.1 | Streamer service + frame decimation | 5.1.story.md |
| S5.2 | WebSocket endpoint + control handling | 5.2.story.md |
| S5.3 | SSE fallback endpoint (frames) | 5.3.story.md |
| S6.1 | Runs List view (presentational UI) | 6.1.story.md |
| S6.2 | Run Detail playback view (charts + controls) | 6.2.story.md |
| S6.3 | WS hook, Worker parsing, and overlays wiring | 6.3.story.md |
| S7.1 | Logging and minimal metrics (operability) | 7.1.story.md |
| S7.2 | Retention and pruning of runs/artifacts | 7.2.story.md |
| S7.3 | Performance budgets validation (latency, jitter, storage) | 7.3.story.md |
| S7.4 | Error handling and catalog status transitions | 7.4.story.md |

### Usage Notes
- When referencing a specific acceptance criterion in a commit or PR: "Implements S2.2-AC-3; validates via E2-TC-1/TC-2"
- The numbering of ACs/TCs follows the existing numbered lists in each markdown file
- If ACs/TCs are reordered in the future, update references accordingly or pin by quoting the text

---

## 3. Story-to-QA Mapping

**Purpose**: Map each story's acceptance criteria (AC) to the corresponding Epic QA checklist test cases, for traceability and test planning.

### Epic 1 — Backend Skeleton
- **Story 1.1** — Backend skeleton: health endpoint and app wiring
  - QA: [Epic 1](./qa/epic-1-acceptance-checklist.md) — TC1 (Health), TC3 (Structure & non-blocking)
- **Story 1.2** — Backend skeleton: WebSocket echo endpoint
  - QA: [Epic 1](./qa/epic-1-acceptance-checklist.md) — TC2 (WS echo), TC3 (Structure & non-blocking)
- **Story 1.3** — Backend skeleton: Backtests routes stubs
  - QA: [Epic 1](./qa/epic-1-acceptance-checklist.md) — TC3 (Structure), plus stub behavior validated informally until Epic 2

### Epic 2 — Catalog Adapter and Models
- **Story 2.1** — Catalog models + SQLite adapter (list/get runs)
  - QA: [Epic 2](./qa/epic-2-acceptance-checklist.md) — TC1 (GET /backtests empty), TC2 (GET /backtests/{id} 404), TC3 (Model alignments)
- **Story 2.2** — List runs API (filters, pagination, ordering)
  - QA: [Epic 2](./qa/epic-2-acceptance-checklist.md) — TC1 (List shape) extended; add filter/pagination verification
- **Story 2.3** — Get run API (detail by id)
  - QA: [Epic 2](./qa/epic-2-acceptance-checklist.md) — TC2 (404), TC3 (shape alignment)

### Epic 3 — Data Ingest and Derive
- **Story 3.1** — Databento ingestion CLI (DBN TRADES+TBBO)
  - QA: [Epic 3](./qa/epic-3-acceptance-checklist.md) — TC1 (Ingest), TC2 (Filesystem), TC5 (Determinism smoke)
- **Story 3.2** — Derive 1m bars + minute TBBO aggregates (Parquet)
  - QA: [Epic 3](./qa/epic-3-acceptance-checklist.md) — TC1 (Derive), TC2 (Filesystem), TC4 (Manifest integrity), TC5 (Determinism)
- **Story 3.3** — Upsert Dataset in Catalog (SQLite) with Manifest
  - QA: [Epic 3](./qa/epic-3-acceptance-checklist.md) — TC3 (Catalog row upsert)

### Epic 4 — Backtest Runner & Artifacts
- **Story 4.1** — Nautilus adapter integration (BacktestRunnerPort)
  - QA: [Epic 4](./qa/epic-4-acceptance-checklist.md) — Contributes to TC1–TC4 (execution, artifacts, metrics)
- **Story 4.2** — Run job + write artifacts
  - QA: [Epic 4](./qa/epic-4-acceptance-checklist.md) — TC1 (Create run), TC2 (Completion), TC3 (Artifacts), TC4 (Metrics)
- **Story 4.3** — Idempotent POST /backtests (enqueue + status)
  - QA: [Epic 4](./qa/epic-4-acceptance-checklist.md) — TC1–TC2 (Create/Status), TC5 (Idempotency)

### Epic 5 — Playback Streaming
- **Story 5.1** — Streamer service + frame decimation
  - QA: [Epic 5](./qa/epic-5-acceptance-checklist.md) — Supports TC1 (FPS), TC3 (Dropped counter), TC5 (hb/end/err)
- **Story 5.2** — WebSocket endpoint + control handling
  - QA: [Epic 5](./qa/epic-5-acceptance-checklist.md) — TC1 (FPS), TC2 (Controls), TC3 (Backpressure), TC5 (hb/end/err)
- **Story 5.3** — SSE fallback endpoint (frames)
  - QA: [Epic 5](./qa/epic-5-acceptance-checklist.md) — TC4 (SSE fallback)

### Epic 6 — Frontend MVP
- **Story 6.0** — UX artifacts: wireframes and FE component map
  - QA: [Epic 6](./qa/epic-6-acceptance-checklist.md) — Supports TC1/TC2 by providing design artifacts
- **Story 6.1** — Runs List view (presentational UI)
  - QA: [Epic 6](./qa/epic-6-acceptance-checklist.md) — TC1 (Runs List), TC3 (Presentational components)
- **Story 6.2** — Run Detail playback view (charts + controls)
  - QA: [Epic 6](./qa/epic-6-acceptance-checklist.md) — TC2 (Run Detail playback), TC4 (Performance sanity)
- **Story 6.3** — WS hook, Worker parsing, and overlays wiring
  - QA: [Epic 6](./qa/epic-6-acceptance-checklist.md) — Supports TC2 (playback stability), TC3 (presentational-only rule)

### Epic 7 — Hardening & NFRs
- **Story 7.1** — Logging and minimal metrics (operability)
  - QA: [Epic 7](./qa/epic-7-acceptance-checklist.md) — TC1 (Logging), TC2 (Minimal metrics)
- **Story 7.2** — Retention and pruning of runs/artifacts
  - QA: [Epic 7](./qa/epic-7-acceptance-checklist.md) — TC3 (Retention/pruning)
- **Story 7.3** — Performance budgets validation (latency, jitter, storage)
  - QA: [Epic 7](./qa/epic-7-acceptance-checklist.md) — TC4 (Performance budgets)
- **Story 7.4** — Error handling and catalog status transitions
  - QA: [Epic 7](./qa/epic-7-acceptance-checklist.md) — TC5 (Error handling & transitions)

---

## 4. NFR Validation Framework

**Purpose**: Validate Non-Functional Requirements from PRD and Architecture specifications.

### Environment Setup
- **API base**: http://127.0.0.1:8000
- **Node**: v22+ (for WS bench script)
- **Host**: Fill in your machine specs (CPU/RAM)

### Validation Procedures

#### 1. Setup
- Start API: `make start-backend`
- Ensure at least one completed run exists (create via API or CLI if needed)

#### 2. REST Latency Testing (p50/p95)
```bash
./scripts/bench_rest.sh http://127.0.0.1:8000 200
```
**Expected Output:**
- [bench_rest] GET /backtests x200 → p50=4.2 ms p95=12.8 ms
- [bench_rest] GET /backtests/<id> x200 → p50=3.7 ms p95=9.9 ms

#### 3. WebSocket Streaming Performance
```bash
node scripts/bench_ws.js ws://127.0.0.1:8000/backtests/<run_id>/ws 10
```
**Expected Output:**
```json
{ "frames": 280, "fps": 28.0, "p50_ms": 33, "p95_ms": 51 }
```

#### 4. Storage Footprint Analysis
```bash
./scripts/measure_sizes.sh data
```
**Expected Output:**
- derived: 120 MiB
- backtests: 340 MiB
- raw: 1.8 GiB
- per-run (top 10): run_abc 12000 KiB, run_def 8000 KiB

### Acceptance Targets (MVP)
- **REST p95**: Under 100 ms on developer laptop
- **WebSocket**: 25–30 FPS effective playback with p95 inter-frame under 80 ms (local)
- **Storage**: Per derived symbol-year under 1 GiB; per run artifacts under 100 MiB

### Notes
- Scripts provide consistent, comparable local measurements
- For CI/regression gates, consider running REST bench with small COUNT (e.g., 20) to keep CI time low

---

## 5. Performance Testing Plan

**Purpose**: Comprehensive performance validation aligned with PRD §2.2 and Architecture §Non-Functional requirements.

### Test Environment
- **Hardware**: Apple Silicon M2 (16 GB), macOS
- **Dataset**: AAPL 2023 derived per baselines (1m bars + TBBO aggregates)
- **Build**: Local dev; backend in debug acceptable for MVP measurements

### Metrics and Targets

#### Playback (WebSocket Primary)
- **Avg FPS**: ≈ 30
- **p95 dropped-frame**: ≤ 5%
- **p99 frame latency**: ≤ 200 ms

#### REST API
- **/backtests list p95 latency**: ≤ 150 ms (100 runs)
- **/backtests/{id} get**: ≤ 100 ms

#### Backtest Runtime (Cached Data)
- **Baseline run**: ≤ 30 s E2E

#### Storage Budgets
- **1m bars + TBBO per symbol-year**: ≤ 250 MB
- **Per-run artifacts**: ≤ 50 MB

### Instrumentation

#### Server
- **Structured logs**: timestamps, run_id, frame counters (produced/sent/dropped), per-frame latency
- **Metrics counters** (minimal): frames_produced, frames_sent, frames_dropped

#### Client
- **Worker measures**: inter-frame arrival jitter and render latency
- **Periodic summaries**: logged for analysis

### Test Procedures

1. **Dataset Preparation**
   ```bash
   make data SYMBOL=AAPL YEAR=2023
   # Verify bars manifest includes calendar_version and hashes
   ```

2. **Backtest Baseline**
   ```bash
   make backtest SYMBOL=AAPL FROM=2023-01-01 TO=2023-12-31 FAST=20 SLOW=50 SPEED=60 SEED=42
   # Verify artifacts exist and manifest recorded
   ```

3. **Playback WebSocket Testing**
   - Connect to `ws://localhost:8000/backtests/{run_id}/ws`
   - Run sequence: pause → play → speed=60 → seek mid-range → play to end
   - Record: avg FPS, p95 dropped-frame ratio, p99 frame latency from logs/counters

4. **SSE Fallback Testing**
   - GET `/backtests/{id}/stream?speed=60`
   - Verify frames stream; check fallback stability (no control)

5. **REST Latency Testing**
   - Seed catalog with N ~ 100 runs (synthetic acceptable for timing)
   - Measure p95 for list/get via repeated calls (exclude warm-up)

6. **Storage Footprint Analysis**
   - Measure sizes of derived bars and per-run artifacts
   - Compare to budgets

### Reporting
Produce a short run report per test with:
- Environment details (machine, versions)
- Metrics table (targets vs observed)
- Notable logs (anomalies, error codes)

### Acceptance Criteria
All targets within specified thresholds; deviations documented with rationale and mitigation plan.

---

**Cross-References**
- **Individual Epic Checklists**: [`docs/qa/epic-N-acceptance-checklist.md`](./qa/)
- **Detailed Test Gates**: [`docs/qa/gates/`](./qa/gates/)
- **Story Files**: [`docs/stories/`](./stories/)
- **Metrics Definitions**: [`docs/metrics/run-metrics-definitions.md`](./metrics/run-metrics-definitions.md)

---

**Note**: This document consolidates QA documentation previously scattered across multiple files. BMAD-compliant numbered sequences (epic checklists, stories, test gates) are preserved in their original locations.
