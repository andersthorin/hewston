# ADR-008 — Plan Schema and Manifest Versioning

Status
- Proposed

Context
- Agentic Mode relies on deterministic plans and reproducible manifests. As schemas evolve, we need versioning, hashing, and idempotency.

Decision
- Define versioned JSON schemas for Plan and Manifest. Compute a stable plan_hash (sha256 over normalized JSON) to support idempotent execution.

Plan schema (v1)
- Fields: version, from, to, universe{included[], excluded[{symbol,reason,details?}]}, strategies[{id, params}], guardrails{checks[{name, ok, details}]}, plan_hash.
- Optional: notes, warnings.

Manifest schema (v1)
- Fields: plan (embedded), run_ids[], code_hash, seed(s), created_at, stages timeline (plan→start→finish→post), metrics_summary.

Idempotency
- start_agentic_run(plan_id|plan) must detect duplicate plan_hash and avoid duplicate submissions; return existing run_ids.

Observability
- Persist Plan and Manifest JSON; expose in UI and allow download. Add schema version to filenames when practical.

Migration
- When schema changes, bump version and add compatibility shims. Record breaking changes in a migration note.

Links
- Epic 16 PRD/Plan
- Epic 21 PRD/Plan

