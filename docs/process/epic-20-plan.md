# Epic 20 Plan — Nautilus Multi‑Strategy Runner (Equities/XNAS)

Objective
- Run multiple strategy instances per symbol (and optionally small multi‑symbol bundles) with Nautilus Trader, including streaming.

Phases and Tasks
1) Runner API extension (owner: BE)
   - Accept instrument_ids: list[str] and strategies: list[StrategySpec]
   - Instantiate one strategy per (symbol×strategy) as needed
   - Add strategies before data; OMS=HEDGING
2) BacktestRunConfig wiring (owner: BE)
   - Build BacktestRunConfig with multiple strategies + BacktestDataConfig entries
   - Enable streaming mode for large datasets
3) Metrics aggregation (owner: BE)
   - Extract per‑strategy and portfolio‑level metrics
   - Aggregate across bundles (if multiple runs)
4) Job integration (owner: BE)
   - start_agentic_run submits one or many runs; persist artifacts and manifest
5) Smoke tests (owner: QA/BE)
   - Validate multi‑strategy per symbol and small multi‑symbol bundles

Dependencies
- Epic 17 (strategy set), Epic 19 (risk/metrics), Epic 18 (universe)

Acceptance Criteria
- A run can execute multiple strategies on one symbol
- Optional small multi‑symbol bundles supported
- Streaming validated on longer ranges; artifacts and metrics persisted

