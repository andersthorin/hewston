# Epic 21 Addendum — Architect Review

Key Additions
- Manifest completeness: include plan (embedded), plan schema version, plan_hash, code_hash, seed(s), and audit timeline (plan → start → finish → post-analysis).
- Versioning: version Plan and Manifest schemas; define migration rules; see ADR-008.
- Results insights: stability flags (equity kink/drawdown clustering) and cost sensitivity notes.

New Stories
- 21.5 — Observability: plan versioning and audit timeline
- 21.6 — Seed control and reproducibility toggle in UI


Feature Flag and Consent
- Gate Agentic Auto-Selection behind an admin feature flag initially.
- First-time Agentic Mode use shows a consent prompt: "I understand this will auto-select universe and strategies within guardrails."
- Expose feature flag in admin settings; default OFF.

References
- ADR-008 Plan Schema and Manifest Versioning
- ADR-005 Metrics & Guardrails Baseline

