# Story Standards: Definition of Ready (DoR) and Definition of Done (DoD)

Status: v0.1 — Apply to all stories in docs/stories/.

## Definition of Ready (DoR)
A story is READY to start when:
- Context: Purpose and scope are clear; non-goals (if any) are noted
- Dependencies: "Depends on" and "Blocks" are listed
- References: Links to canonical docs (baselines, OpenAPI, WS protocol, error codes)
- Acceptance Criteria: Measurable, testable, unambiguous (include NFRs where relevant)
- Testability: QA mapping exists (story → Epic QA checklist items)
- Environment: Any required secrets/env noted (.env.example)

## Definition of Done (DoD)
A story is DONE when:
- Implementation: ACs met; code organized per Source Tree and coding standards
- Quality: Lint/format clean; unit/integration tests added/updated and pass locally
- Determinism/Performance: Relevant tolerances met (see baselines & perf plan)
- Documentation: API/WS docs updated if affected; PRD/Architecture shards remain aligned
- Observability: Structured logs/counters added when applicable
- Traceability: Commits/PR reference Story ID and QA case IDs

## Usage
- Include a short DoR checklist at the top of each story (or link to this doc) and ensure ACs cite canonical documents.
- Include/retain a DoD section per story; use the above criteria as the baseline.

