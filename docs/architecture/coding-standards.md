# Coding Standards and Conventions (Authoritative)

Status: v0.1 (aligns with PRD §2, §4 and Architecture §Non‑Functional, §API Contracts)

## General Principles
- Determinism first: identical inputs → identical artifacts (hashes); record seeds, calendar_version, tz, code_hash, env_lock in manifests.
- Separation of concerns: presentational UI vs. data/logic; API handlers vs. background jobs.
- Async by default in API; CPU‑bound work in subprocesses (Typer jobs).
- Structured logs (JSON) with request_id and run_id for traceability.

## Python (Backend)
- Style & Lint
  - Ruff 0.6.x (lint) with default rules + import sorting.
  - Black 24.8.x (format) with default line length (88) unless otherwise decided.
  - Type hints required on public functions; prefer dataclasses or Pydantic models for payloads.
- Project Structure
  - Follow Source Tree (see docs/architecture/source-tree.md). Keep ports small and stable.
  - Do not import adapters from services; depend on ports (interfaces) and inject implementations.
- FastAPI
  - Handlers are thin: validate, delegate to services, return models. Never run CPU‑bound work in handlers.
  - Use Pydantic v2 models for request/response schemas; align with OpenAPI.
  - Uniform error shape: { error: { code, message, details? } }.
- Jobs (Typer)
  - Commands: data (ingest/derive), backtest. Share ports/adapters with services.
  - Emit structured progress logs; write manifests/artifacts atomically.
- Logging
  - structlog JSON; include request_id, run_id, idempotency_key where relevant.
  - INFO for control flow; WARN/ERROR include codes and key fields.
- Time & Timezones
  - Persist UTC timestamps; UI renders America/New_York.
  - Pin NASDAQ calendar version; explicit DST handling.
- Determinism
  - Stable sort keys for processing; seeded randomness where applicable.
  - Compute SHA‑256 for raw/derived artifacts; compute input_hash for idempotent POST /backtests.
- Testing
  - pytest; fixtures for DBN→1m bars; adapter conformance; seed determinism tests; E2E smoke baseline.
  - Keep unit tests close to code; integration tests may live under tests/.

## TypeScript/Frontend
- Philosophy
  - Presentational components only render; they never fetch, compute business data, or mutate state outside props/local UI state.
  - Containers/hooks/services handle fetching, parsing, validation, and orchestration.
- Style & Lint
  - ESLint 9.10.x with recommended + TypeScript plugin; Prettier 3.3.x for formatting.
  - Naming: PascalCase components; camelCase functions/vars; UPPER_SNAKE for constants.
  - Hooks prefixed with use* and reside under src/services or src/containers.
- State/Data
  - TanStack Query for remote data; stable query keys; cache lifetimes explicit.
  - Zod for boundary validation (API responses, WS frames).
- Streaming (WS/SSE)
  - Use a dedicated hook (src/services/ws.ts) and a Worker (src/workers/streamParser.ts) to parse frames off main thread.
  - Handle heartbeats, backpressure (drop oldest), and decimation at server guidance.
- Testing
  - Vitest for unit tests; React Testing Library for components. Avoid coupling to implementation details.
  - Snapshot tests sparingly (presentational components). Prefer behavioral tests.

## Commits, Reviews, and Branching
- Commit style: Conventional Commits (e.g., feat:, fix:, docs:, refactor:, test:, chore:).
- Small, reviewable PRs; link Story ID (e.g., S2.3) and QA IDs where applicable.
- Each PR must pass lint, format, and tests locally.

## Makefile and Scripts
- Use Make targets for common flows (setup, start, data, backtest, db-apply, lint, format, test).
- Do not embed secrets in scripts; read from env (see .env.example).

## Error Handling & API Contracts
- REST errors follow the uniform shape; map domain errors to typed codes.
- Idempotent create: accept Idempotency-Key; return 200 EXISTS on repeat.
- SSE endpoint emits event: frame with StreamFrame payload.

## Documentation
- Keep docs/architecture.md and shards in sync; update cross-links when interfaces or boundaries change.
- Update docs/api/openapi.yaml alongside any API changes; run a basic linter if available.
- Maintain QA mapping (docs/qa/story-to-qa-mapping.md) when stories or checklists change.

## Definition of Done (DoD) — Minimum
- Code adheres to this standard (lint/format clean).
- Tests updated/added and passing locally; determinism checks where relevant.
- Docs (API/architecture) updated; manifests capture new/relevant fields.
- Logs include run_id and key fields for new flows.

