# Epic 4 — Backtest Runner & Artifacts: Acceptance Test Checklist
Epic ID: E4



Preconditions
- Dataset from Epic 3 READY in catalog
- Backend skeleton + catalog adapter in place

Test Cases
1) Create run (AC)
   - Step: POST /backtests with { dataset_id, strategy_id:"sma_crossover", params:{fast:20,slow:50}, seed, slippage_fees, speed }
   - Verify: 202 { run_id, status:"QUEUED" }

2) Completion and status
   - Step: Poll GET /backtests/{run_id}
   - Verify: status transitions to DONE; duration_ms populated

3) Artifacts written
   - Verify: data/backtests/{run_id}/ contains metrics.json, equity.parquet, orders.parquet, fills.parquet, run-manifest.json
   - Sanity: files non-empty; manifest has code_hash, env_lock, dataset refs

4) Metrics recorded
   - Verify: run_metrics row inserted with non-null computed_at; key metrics populated

5) Idempotency
   - Step: Repeat POST with same Idempotency-Key and identical body
   - Verify: 200 { run_id:same, status:"EXISTS" }

Pass/Fail Criteria
- End-to-end run completes within ~30s on cached data; artifacts and catalog rows correct; idempotency works

Artifacts
- Save POST/GET transcripts; ls -l of artifacts directory; sqlite3 queries for runs/run_metrics rows

