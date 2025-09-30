# Epic 3 — Data Ingest and Warehouse Materialization: Acceptance Test Checklist
Epic ID: E3



Preconditions
- Databento API key configured in environment
- `make db-apply` done; backend jobs wired

Test Cases
1) Warehouse materialization command (AC)
   - Step: `make materialize-day SYMBOL=AAPL DATE=2024-10-01 VENUE=XNAS`
   - Verify: Command completes without error; logs show quotes_ingest, trades_aggregate, materialize_bars phases

2) Filesystem artifacts
   - Verify: Raw DBN cached under data/raw/...; warehouse outputs under data/warehouse/{quotes,trades_agg/{1min,1h},bars/mid_{1min,1h}} partitioned by venue/symbol/date
   - Check sizes within rough expectations; no zero-byte files

3) Catalog row upsert
   - Step: Open SQLite and query `SELECT * FROM datasets WHERE dataset_id LIKE 'AAPL-2023-%'`
   - Verify: Row exists; status=READY; paths JSON lists populated; tz and calendar_version set

4) Bars correctness
   - Verify: For a regular RTH day, 1-minute bars count near 390; OHLC plausible; non-negative volume; 1-hour bars present

5) Idempotence (smoke)
   - Step: Re-run `make materialize-day SYMBOL=AAPL DATE=2024-10-01 VENUE=XNAS`
   - Verify: Idempotent behavior: either skip if already materialized, or overwrite deterministically; bar counts unchanged

Pass/Fail Criteria
- Artifacts exist; catalog updated; manifest contains required fields; idempotence holds

Artifacts
- Sample manifest JSON; sqlite3 .dump of datasets row

