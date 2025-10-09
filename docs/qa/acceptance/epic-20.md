# QA Acceptance — Epic 20 Nautilus Multi‑Strategy Runner

Scope
- Multiple strategies per symbol; optional small multi‑symbol bundles; streaming

Test Matrix
1) Multi‑strategy per symbol
- 2+ strategies on one instrument_id; OMS=HEDGING; artifacts present

2) Small multi‑symbol bundles
- 3–5 symbols per run; metrics aggregated; memory within bounds

3) Streaming
- Streaming protocol: chunked data batches; no memory exhaustion; correct final results

4) Metrics provenance
- KPIs flagged as engine‑derived vs post‑processed; present in metrics.json

5) Performance envelope (M1)
- Stress tests report RSS/time vs bundle size; orchestrator caps updated accordingly

Artifacts
- Run manifests and metrics validated; streaming logs retained for review

