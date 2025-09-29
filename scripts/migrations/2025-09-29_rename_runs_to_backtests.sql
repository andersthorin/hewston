-- Migration: Rename runs -> backtests (and run_metrics -> backtest_metrics)
-- WARNING: This migration renames physical tables. Ensure the application code
-- has been updated to write to `backtests` and `backtest_metrics` before applying.
-- During migration, legacy compatibility views are created so SELECTs against
-- `runs` and `run_metrics` still work. However, INSERT/UPDATE/DELETE on views
-- will fail unless INSTEAD OF triggers are added. Plan the cutover accordingly.

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1) Rename primary tables
ALTER TABLE runs RENAME TO backtests;
ALTER TABLE run_metrics RENAME TO backtest_metrics;

-- 2) Recreate indexes if any referenced old names (adjust as needed)
-- Example (uncomment/adjust if these exist in your DB):
-- DROP INDEX IF EXISTS idx_runs_created_at;
-- CREATE INDEX IF NOT EXISTS idx_backtests_created_at ON backtests(created_at);


COMMIT;
PRAGMA foreign_keys = ON;

-- Rollback plan:
-- BEGIN TRANSACTION;
-- DROP VIEW IF EXISTS run_metrics;
-- DROP VIEW IF EXISTS runs;
-- ALTER TABLE backtest_metrics RENAME TO run_metrics;
-- ALTER TABLE backtests RENAME TO runs;
-- COMMIT;

