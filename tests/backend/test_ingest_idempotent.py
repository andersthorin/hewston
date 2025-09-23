import os
import tempfile
from pathlib import Path

import backend.jobs.ingest as ingest


def test_ingest_idempotent_and_force(tmp_path, monkeypatch):
    # Ensure env present
    monkeypatch.setenv("DATABENTO_API_KEY", "test-key")
    monkeypatch.setenv("HEWSTON_DATA_DIR", str(tmp_path))

    sizes1 = ingest.ingest_databento("AAPL", 2023, force=False)
    # Two products
    assert set(sizes1.keys()) == {"TRADES", "TBBO"}

    base = Path(tmp_path) / "raw/databento/AAPL/2023"
    f_trades = base / "TRADES.dbn.zst"
    f_tbbo = base / "TBBO.dbn.zst"
    assert f_trades.exists() and f_tbbo.exists()
    s_trades_1 = f_trades.stat().st_size
    s_tbbo_1 = f_tbbo.stat().st_size
    assert s_trades_1 > 0 and s_tbbo_1 > 0

    # Second run without force should skip and keep sizes
    sizes2 = ingest.ingest_databento("AAPL", 2023, force=False)
    assert sizes2["TRADES"] == s_trades_1
    assert sizes2["TBBO"] == s_tbbo_1

    # With force, files are rewritten (sizes remain same in stub)
    sizes3 = ingest.ingest_databento("AAPL", 2023, force=True)
    assert sizes3["TRADES"] == s_trades_1
    assert sizes3["TBBO"] == s_tbbo_1

