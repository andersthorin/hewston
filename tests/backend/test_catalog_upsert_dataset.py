import json
import os
import sqlite3
from pathlib import Path

from backend.adapters.databento import ensure_dataset
from backend.adapters.sqlite_catalog import SqliteCatalog
from backend.jobs.ingest import ingest_databento
from backend.jobs.derive import derive_bars


def test_ensure_dataset_upserts_and_is_idempotent(tmp_path, monkeypatch):
    # Point data dir and set API key
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HEWSTON_CATALOG_PATH", str(tmp_path / "catalog.sqlite"))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

    # Ensure dataset (this runs ingest->derive->upsert)
    dsid1 = ensure_dataset("AAPL", 2023, force=False)
    assert dsid1 == "AAPL-2023-1m"

    db_path = Path(os.environ["HEWSTON_CATALOG_PATH"])  # set above
    assert db_path.exists()

    # Verify row content
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dsid1,)).fetchone()
        assert row is not None
        assert row["symbol"] == "AAPL"
        assert row["from_date"] == "2023-01-01"
        assert row["to_date"] == "2023-12-31"
        assert row["status"] == "READY"
        assert row["bars_manifest_path"].endswith("bars_manifest.json")
        assert row["size_bytes"] > 0
        prods = json.loads(row["products_json"])  # ["TRADES","TBBO"]
        assert set(prods) == {"TRADES", "TBBO"}

    # Re-run and ensure idempotency (no duplicate rows; same dataset_id)
    dsid2 = ensure_dataset("AAPL", 2023, force=False)
    assert dsid2 == dsid1
    with sqlite3.connect(db_path) as conn:
        n = conn.execute("SELECT COUNT(1) FROM datasets WHERE dataset_id = ?", (dsid1,)).fetchone()[0]
        assert n == 1

