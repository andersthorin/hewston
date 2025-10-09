# Epic 20 Addendum — Architect Review

Key Additions
- Streaming run protocol: for large ranges, use chunked data processing — add initial batch, run(streaming=True), clear_data(), add next batch… then final run(streaming=False) or end().
- Prefer building BacktestRunConfig/BacktestNode for clarity as config grows; low-level API is acceptable initially.
- Metrics extraction provenance: record whether KPIs came from Nautilus internals vs post-processing; include in metrics.json.
- Memory/footprint validation on M1: stress tests to define safe symbol/strategy bundle sizes.

New Stories
- 20.4 — Streaming protocol smoke test
- 20.5 — Memory footprint stress test on M1

References
- Nautilus docs: streaming guidance
- Epics 18, 19 integration

