# QA Acceptance — Epic 21 Agentic Ops and Guardrails

Scope
- Ops flow (user-triggered), manifests/history, ranking/insights, feature flag/consent

Test Matrix
1) Ops flow
- User must click Start; no autonomous runs
- Audit timeline populated (plan → start → finish → post)

2) Manifests/history
- Manifest includes plan (v1), plan_hash, code_hash, seeds, metrics_summary
- History view exposes manifest; downloadable; diff view between runs

3) Ranking/insights
- Sorting and filtering by KPIs; insights reflect stability and cost-sensitivity

4) Feature flag & consent
- Flag OFF hides agentic UI and rejects agentic endpoints
- First-time consent modal appears; consent recorded and present in manifest (consented_by/at)

Artifacts
- Manifests validated vs schema; screenshots of history/diff and ranking views

