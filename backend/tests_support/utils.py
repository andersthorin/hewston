"""
Shared test utilities for backend test suites.
Moved from top-level tests/utils.py to reduce duplication
and keep all backend test code under backend/.
"""

from pathlib import Path
from typing import Any, Dict, Optional



def setup_test_environment(
    tmp_path: Path,
    monkeypatch: Any,
    *,
    api_key: str = "test-key",
    additional_env: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Set up common test environment variables.

    Returns a dict of environment variables applied.
    """
    env_vars = {
        "HEWSTON_DATA_DIR": str(tmp_path),
        "HEWSTON_CATALOG_PATH": str(tmp_path / "catalog.sqlite"),
        "DATABENTO_API_KEY": api_key,
    }

    if additional_env:
        env_vars.update(additional_env)

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


def create_test_data_structure(base_path: Path) -> Dict[str, Path]:
    """Create a standard test data directory structure."""
    paths = {
        "raw_databento": base_path / "raw" / "databento",
        "derived_bars": base_path / "derived" / "bars",
        "backtests": base_path / "backtests",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def assert_file_exists_and_not_empty(file_path: Path, min_size: int = 1) -> None:
    """Assert that a file exists and is at least min_size bytes."""
    assert file_path.exists(), f"File does not exist: {file_path}"
    assert file_path.stat().st_size >= min_size, f"File is too small: {file_path}"


def get_test_symbol_year() -> tuple[str, int]:
    """Get the standard test symbol and year."""
    return "AAPL", 2023

