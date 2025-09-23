import json
import os
from pathlib import Path

import backend.jobs.ingest as ingest
import backend.jobs.derive as derive


def test_derive_bars_produces_parquet_and_manifest(tmp_path, monkeypatch):
    # Env setup
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))

    # Seed raw files via ingest
    ingest.ingest_databento("AAPL", 2023, force=False)

    # Derive
    m1 = derive.derive_bars("AAPL", 2023, force=False)

    derived_dir = Path(tmp_path) / "derived/bars/AAPL/2023"
    bars = derived_dir / "bars_1m.parquet"
    tbbo = derived_dir / "tbbo_1m.parquet"
    manifest = derived_dir / "bars_manifest.json"

    assert bars.exists() and tbbo.exists() and manifest.exists()

    j = json.loads(manifest.read_text())
    assert j["symbol"] == "AAPL"
    assert j["interval"] == "1m"
    assert set(j["output_hashes"].keys()) == {"bars_1m.parquet", "tbbo_1m.parquet"}
    assert len(j["output_hashes"]["bars_1m.parquet"]) == 64

    # Re-run without force should keep manifest identical
    m2 = derive.derive_bars("AAPL", 2023, force=False)
    assert m1 == m2

    # Force run should rewrite but hashes remain the same (deterministic)
    m3 = derive.derive_bars("AAPL", 2023, force=True)
    assert m3["output_hashes"] == m1["output_hashes"]

