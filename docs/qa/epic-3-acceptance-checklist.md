# Epic 3 — Data Ingest and Derive: Acceptance Test Checklist
Epic ID: E3



Preconditions
- Databento API key configured in environment
- `make db-apply` done; backend jobs wired

Test Cases
1) Ingest + Derive command (AC)
   - Step: `make data SYMBOL=AAPL YEAR=2023`
   - Verify: Command completes without error; logs show ingest and derive phases

2) Filesystem artifacts
   - Verify: Raw DBN cached under data/raw/...; derived Parquet under data/derived/bars/...
   - Check sizes within rough expectations; no zero-byte files

3) Catalog row upsert
   - Step: Open SQLite and query `SELECT * FROM datasets WHERE dataset_id LIKE 'AAPL-2023-%'`
   - Verify: Row exists; status=READY; paths JSON lists populated; tz and calendar_version set

4) Manifest integrity
   - Verify: bars manifest JSON includes input_hashes and output_hashes; dates/interval correct

5) Determinism (smoke)
   - Step: Re-run `make data SYMBOL=AAPL YEAR=2023`
   - Verify: No duplicate dataset rows; hashes unchanged; idempotent behavior

Pass/Fail Criteria
- Artifacts exist; catalog updated; manifest contains required fields; idempotence holds

Artifacts
- Sample manifest JSON; sqlite3 .dump of datasets row

