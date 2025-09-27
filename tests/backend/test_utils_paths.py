"""
Tests for backend/utils/paths.py utility functions.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.utils.paths import (
    get_base_data_dir,
    get_catalog_path,
    get_raw_databento_dir,
    get_derived_bars_dir,
    get_backtests_dir,
    ensure_dir,
)


class TestPathUtilities:
    """Test suite for path utility functions."""

    def test_get_base_data_dir_default(self):
        """Test get_base_data_dir returns default 'data' directory."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_base_data_dir()
            assert result == Path("data")

    def test_get_base_data_dir_from_env(self, monkeypatch):
        """Test get_base_data_dir respects HEWSTON_DATA_DIR environment variable."""
        custom_path = "/custom/data/path"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_path)
        
        result = get_base_data_dir()
        assert result == Path(custom_path)

    def test_get_catalog_path_default(self):
        """Test get_catalog_path returns correct default path."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_catalog_path()
            expected = Path("data") / "catalog.db"
            assert result == expected

    def test_get_catalog_path_with_custom_base(self, monkeypatch):
        """Test get_catalog_path with custom base directory."""
        custom_base = "/custom/base"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_base)
        
        result = get_catalog_path()
        expected = Path(custom_base) / "catalog.db"
        assert result == expected

    def test_get_raw_databento_dir_default(self):
        """Test get_raw_databento_dir returns correct default path."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_raw_databento_dir()
            expected = Path("data") / "raw" / "databento"
            assert result == expected

    def test_get_raw_databento_dir_with_custom_base(self, monkeypatch):
        """Test get_raw_databento_dir with custom base directory."""
        custom_base = "/custom/base"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_base)
        
        result = get_raw_databento_dir()
        expected = Path(custom_base) / "raw" / "databento"
        assert result == expected

    def test_get_backtests_dir_default(self):
        """Test get_backtests_dir returns correct default path."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_backtests_dir()
            expected = Path("data") / "backtests"
            assert result == expected

    def test_get_backtests_dir_with_custom_base(self, monkeypatch):
        """Test get_backtests_dir with custom base directory."""
        custom_base = "/custom/base"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_base)
        
        result = get_backtests_dir()
        expected = Path(custom_base) / "backtests"
        assert result == expected

    def test_get_derived_bars_dir_default(self):
        """Test get_derived_bars_dir returns correct default path."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_derived_bars_dir()
            expected = Path("data") / "derived" / "bars"
            assert result == expected

    def test_get_derived_bars_dir_with_custom_base(self, monkeypatch):
        """Test get_derived_bars_dir with custom base directory."""
        custom_base = "/custom/base"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_base)

        result = get_derived_bars_dir()
        expected = Path(custom_base) / "derived" / "bars"
        assert result == expected

    def test_get_derived_bars_dir_with_symbol_and_year(self):
        """Test get_derived_bars_dir with symbol and year parameters."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_derived_bars_dir("AAPL", 2023)
            expected = Path("data") / "derived" / "bars" / "AAPL" / "2023"
            assert result == expected

    def test_get_backtests_dir_with_run_id(self):
        """Test get_backtests_dir with run_id parameter."""
        with patch.dict(os.environ, {}, clear=True):
            run_id = "test-run-123"
            result = get_backtests_dir(run_id)
            expected = Path("data") / "backtests" / run_id
            assert result == expected

    def test_path_consistency(self):
        """Test that all path functions return consistent Path objects."""
        with patch.dict(os.environ, {}, clear=True):
            base = get_base_data_dir()
            catalog = get_catalog_path()
            raw_databento = get_raw_databento_dir()
            derived_bars = get_derived_bars_dir()
            backtests = get_backtests_dir()

            # All should be Path objects
            assert isinstance(base, Path)
            assert isinstance(catalog, Path)
            assert isinstance(raw_databento, Path)
            assert isinstance(derived_bars, Path)
            assert isinstance(backtests, Path)

            # All should be relative to the same base (except catalog which has its own path)
            assert raw_databento.parents[1] == base
            assert derived_bars.parents[1] == base
            assert backtests.parent == base

    def test_path_string_conversion(self):
        """Test that paths can be converted to strings properly."""
        with patch.dict(os.environ, {}, clear=True):
            base = get_base_data_dir()
            catalog = get_catalog_path()

            # Should be convertible to strings
            assert str(base) == "data"
            assert str(catalog) == "data/catalog.db"

    def test_environment_variable_precedence(self, monkeypatch):
        """Test that environment variable takes precedence over default."""
        # First test default
        with patch.dict(os.environ, {}, clear=True):
            default_result = get_base_data_dir()
            assert default_result == Path("data")

        # Then test with environment variable
        custom_path = "/env/override/path"
        monkeypatch.setenv("HEWSTON_DATA_DIR", custom_path)
        env_result = get_base_data_dir()
        assert env_result == Path(custom_path)
        assert env_result != default_result

    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test ensure_dir creates directories as needed."""
        test_dir = tmp_path / "test" / "nested" / "path"

        # Directory should not exist initially
        assert not test_dir.exists()

        # ensure_dir should create it
        result = ensure_dir(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir

    def test_ensure_dir_existing_directory(self, tmp_path):
        """Test ensure_dir works with existing directories."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()

        # Should not raise error on existing directory
        result = ensure_dir(test_dir)

        assert test_dir.exists()
        assert result == test_dir
