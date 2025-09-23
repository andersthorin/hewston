# Epic 3 — Data Ingest and Derive

Goal
- Ingest Databento DBN (TRADES + TBBO) and derive deterministic 1‑minute bars + TBBO aggregates (Parquet), recording manifests and catalog rows.

Why (Value)
- Produces reproducible data inputs and deterministic bars for backtests; caches locally for speed.

Scope (In)
- Typer CLI `make data` → backend.jobs.cli `data` command
- adapters/databento.py: ensure_dataset(symbol, from_date, to_date)
- jobs/ingest.py: fetch DBN and cache paths
- jobs/derive.py: derive 1m OHLCV + minute TBBO aggregates with Polars/Arrow
- Write Dataset + DatasetManifest; compute input/output hashes; upsert into SQLite

Out of Scope
- Running backtests or computing metrics

Deliverables
- jobs/cli.py, jobs/ingest.py, jobs/derive.py
- adapters/databento.py (MarketDataPort impl)
- Parquet artifacts under data/derived; raw cache under data/raw

Acceptance Criteria
- `make data SYMBOL=AAPL YEAR=2023` completes successfully
- Dataset row exists in catalog with paths and READY status
- Bars manifest includes calendar_version, tz, input/output hashes

Dependencies
- Epic 2 (Catalog Adapter and Models)

Risks & Mitigations
- Data size and I/O time → stream & chunk; log sizes; document storage budgets
- Calendar/DST inconsistencies → pin calendar version; explicit rules in manifest

Definition of Done
- Deterministic outputs reproducible from manifest; catalog reflects dataset; sizes within budgets

References
- Architecture: Data Models; Catalog Schema; Tech Stack (Polars/Arrow, Databento); Determinism & Reproducibility

