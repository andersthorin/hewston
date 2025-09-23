# ID Scheme for Epics, Stories, ACs, and QA Test Cases

Purpose
- Provide stable identifiers for traceability between stories and QA checklists without changing every file.
- Use these IDs in commits, PR titles, and test reports.

ID Scheme
- Epic IDs: E{n} where n ∈ [1..7]
- Story IDs: S{epicNum}.{storyNum} (e.g., S2.3)
- Story Acceptance Criteria IDs: S{epic}.{story}-AC-{n} where n is the ordinal number in that story’s Acceptance Criteria list
- QA Test Case IDs: E{epic}-TC-{n} where n is the ordinal number in the corresponding Epic acceptance checklist

Examples
- Story “docs/stories/2.3.story.md” → Story ID: S2.3; its second AC → S2.3-AC-2
- QA checklist “docs/qa/epic-4-acceptance-checklist.md” → Epic ID: E4; its third test case → E4-TC-3

Epics
- E1 → docs/qa/epic-1-acceptance-checklist.md (Backend Skeleton)
- E2 → docs/qa/epic-2-acceptance-checklist.md (Catalog Adapter and Models)
- E3 → docs/qa/epic-3-acceptance-checklist.md (Data Ingest and Derive)
- E4 → docs/qa/epic-4-acceptance-checklist.md (Backtest Runner & Artifacts)
- E5 → docs/qa/epic-5-acceptance-checklist.md (Playback Streaming)
- E6 → docs/qa/epic-6-acceptance-checklist.md (Frontend MVP)
- E7 → docs/qa/epic-7-acceptance-checklist.md (Hardening & NFRs)

Stories
- S1.1 → docs/stories/1.1.story.md — Backend skeleton: health endpoint and app wiring
- S1.2 → docs/stories/1.2.story.md — Backend skeleton: WebSocket echo endpoint
- S1.3 → docs/stories/1.3.story.md — Backend skeleton: Backtests routes stubs
- S2.1 → docs/stories/2.1.story.md — Catalog models + SQLite adapter (list/get runs)
- S2.2 → docs/stories/2.2.story.md — List runs API (filters, pagination, ordering)
- S2.3 → docs/stories/2.3.story.md — Get run API (detail by id)
- S3.1 → docs/stories/3.1.story.md — Databento ingestion CLI (DBN TRADES+TBBO)
- S3.2 → docs/stories/3.2.story.md — Derive 1m bars + minute TBBO aggregates (Parquet)
- S3.3 → docs/stories/3.3.story.md — Upsert Dataset in Catalog (SQLite) with Manifest
- S4.1 → docs/stories/4.1.story.md — Nautilus adapter integration (BacktestRunnerPort)
- S4.2 → docs/stories/4.2.story.md — Run job + write artifacts
- S4.3 → docs/stories/4.3.story.md — Idempotent POST /backtests (enqueue + status)
- S5.1 → docs/stories/5.1.story.md — Streamer service + frame decimation
- S5.2 → docs/stories/5.2.story.md — WebSocket endpoint + control handling
- S5.3 → docs/stories/5.3.story.md — SSE fallback endpoint (frames)
- S6.1 → docs/stories/6.1.story.md — Runs List view (presentational UI)
- S6.2 → docs/stories/6.2.story.md — Run Detail playback view (charts + controls)
- S6.3 → docs/stories/6.3.story.md — WS hook, Worker parsing, and overlays wiring
- S7.1 → docs/stories/7.1.story.md — Logging and minimal metrics (operability)
- S7.2 → docs/stories/7.2.story.md — Retention and pruning of runs/artifacts
- S7.3 → docs/stories/7.3.story.md — Performance budgets validation (latency, jitter, storage)
- S7.4 → docs/stories/7.4.story.md — Error handling and catalog status transitions

Usage Notes
- When referencing a specific acceptance criterion in a commit or PR: “Implements S2.2-AC-3; validates via E2-TC-1/TC-2”.
- The numbering of ACs/TCs follows the existing numbered lists in each markdown file.
- If ACs/TCs are reordered in the future, update references accordingly or pin by quoting the text.

