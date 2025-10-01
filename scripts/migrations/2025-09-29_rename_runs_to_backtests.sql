-- Migration: Rename runs -> backtests (and run_metrics -> backtest_metrics)
-- WARNING: This migration renames physical tables and columns. Ensure the application code
-- has been updated to write to `backtests` and `backtest_metrics` before applying.
-- During migration, legacy compatibility views are created so SELECTs against
-- `runs` and `run_metrics` still work. However, INSERT/UPDATE/DELETE on views
-- will fail unless INSTEAD OF triggers are added. Plan the cutover accordingly.

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1) Rename primary tables
ALTER TABLE runs RENAME TO backtests;
ALTER TABLE run_metrics RENAME TO backtest_metrics;

-- 2) Rename primary key columns from run_id -> backtest_id
-- Note: Requires SQLite 3.25+ for RENAME COLUMN; otherwise rebuild table.
ALTER TABLE backtests RENAME COLUMN run_id TO backtest_id;
ALTER TABLE backtest_metrics RENAME COLUMN run_id TO backtest_id;

-- Compatibility views removed as part of clean refactor to canonical backtests schema.
-- Ensure all application code uses 'backtests' and 'backtest_metrics' directly.
-- Recreate any necessary indexes for 'backtests' as needed, e.g.:
-- CREATE INDEX IF NOT EXISTS idx_backtests_created_at ON backtests(created_at);

COMMIT;
PRAGMA foreign_keys = ON;

-- Rollback plan:
-- BEGIN TRANSACTION;
-- DROP VIEW IF EXISTS run_metrics;
-- DROP VIEW IF EXISTS runs;
-- DROP VIEW IF EXISTS runs_list;
-- ALTER TABLE backtest_metrics RENAME COLUMN backtest_id TO run_id;
-- ALTER TABLE backtests RENAME COLUMN backtest_id TO run_id;
-- ALTER TABLE backtest_metrics RENAME TO run_metrics;
-- ALTER TABLE backtests RENAME TO runs;
-- COMMIT;
