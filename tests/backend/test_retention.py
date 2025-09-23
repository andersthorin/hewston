import json
import os
import sqlite3
from pathlib import Path

from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.jobs.retention import select_candidates, apply_deletions, retention_main


def _insert_run(db_path: Path, run_id: str, created_at: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, dataset_id, strategy_id, params_json, seed, slippage_fees_json, speed,
                              code_hash, created_at, status, duration_ms, metrics_path, equity_path, orders_path,
                              fills_path, run_manifest_path, input_hash, idempotency_key)
            VALUES (?, 'ds', 'sma', '{}', 42, '{}', 60, 'x', ?, 'DONE', 10, NULL, NULL, NULL, NULL, 'm', NULL, NULL)
            """,
            (run_id, created_at),
        )


def test_retention_dry_run_and_apply(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    dbp = tmp_path / "catalog.sqlite"
    monkeypatch.setenv("HEWSTON_CATALOG_PATH", str(dbp))

    # Bootstrap catalog
    cat = SqliteCatalog(str(dbp))

    # Create runs with different created_at
    _insert_run(dbp, "r1", "2023-01-01T00:00:00Z")
    _insert_run(dbp, "r2", "2024-01-01T00:00:00Z")
    _insert_run(dbp, "r3", "2025-01-01T00:00:00Z")  # newest

    # Create artifact dirs
    for rid, size in [("r1", 10), ("r2", 20), ("r3", 30)]:
        d = tmp_path / "backtests" / rid
        d.mkdir(parents=True, exist_ok=True)
        (d / "a.bin").write_bytes(b"x" * size)

    # Keep latest 1 -> candidates should be r1 and r2
    cands, kept = select_candidates(keep_latest=1, max_age_days=None)
    ids = [c.run_id for c in cands]
    assert set(ids) == {"r1", "r2"}
    # Sizes computed
    sizes = {c.run_id: c.size_bytes for c in cands}
    assert sizes["r1"] == 10 and sizes["r2"] == 20
    assert kept == ["r3"]

    # Dry run prints summary
    retention_main(keep_latest=1, max_age_days=None, apply=False)
    out = capsys.readouterr().out
    assert '"would_delete_count": 2' in out

    # Apply deletions
    deleted, reclaimed = apply_deletions(cands)
    assert deleted == 2
    assert reclaimed == 30
    # Directories removed
    assert not (tmp_path / "backtests" / "r1").exists()
    assert not (tmp_path / "backtests" / "r2").exists()
    assert (tmp_path / "backtests" / "r3").exists()
    # DB rows gone for r1,r2; r3 remains
    with sqlite3.connect(dbp) as conn:
        rows = conn.execute("SELECT run_id FROM runs").fetchall()
        have = {r[0] for r in rows}
        assert "r3" in have and not {"r1", "r2"} & have

