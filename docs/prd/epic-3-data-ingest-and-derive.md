# Epic 3 — Data Ingest and Warehouse Materialization

Goal
- Ingest Databento DBN (TRADES + TBBO) and materialize deterministic MID bars {1min,1h} + Trades aggregates into a canonical warehouse (Parquet).

Why (Value)
- Produces reproducible data inputs and deterministic bars for backtests; caches locally for speed.

Scope (In)
- Makefile targets: materialize-day, backfill-warehouse
- backend/jobs/quotes_ingest.py: TBBO DBN → QuoteTicks (Parquet)
- backend/jobs/trades_aggregate.py: Trades DBN → {1min,1h} aggregates (Parquet)
- backend/jobs/materialize_bars.py: QuoteTicks + Trades aggregates → MID bars {1min,1h} (Parquet)
- Warehouse replaces Dataset/DatasetManifest; no catalog upsert

Out of Scope
- Running backtests or computing metrics

Deliverables
- backend/jobs/quotes_ingest.py, backend/jobs/trades_aggregate.py, backend/jobs/materialize_bars.py
- Parquet artifacts under data/warehouse; raw cache under data/raw

Acceptance Criteria
- `make materialize-day SYMBOL=AAPL DATE=2024-10-01 VENUE=XNAS` completes successfully
- Warehouse outputs exist at expected paths under data/warehouse (quotes, trades_agg, bars)
- 1m RTH bars count near 390 for regular RTH days; 1h bars present

Dependencies
- Epic 2 (Catalog Adapter and Models)

Risks & Mitigations
- Data size and I/O time → stream & chunk; log sizes; document storage budgets
- Calendar/DST inconsistencies → pin calendar version; explicit rules in manifest

Definition of Done
- Deterministic outputs reproducible from manifest; catalog reflects dataset; sizes within budgets

References
- Architecture: Data Models; Catalog Schema; Tech Stack (Polars/Arrow, Databento); Determinism & Reproducibility

