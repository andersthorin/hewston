"""
Test metrics extraction from Nautilus engine state.
"""

import pytest
from backend.adapters.nautilus import NautilusBacktestRunner


class TestMetricsExtraction:
    """Test suite for metrics extraction from Nautilus."""

    def test_calculate_max_drawdown_empty(self):
        """Test max drawdown calculation with empty equity."""
        runner = NautilusBacktestRunner()
        result = runner._calculate_max_drawdown([])
        assert result == 0.0

    def test_calculate_max_drawdown_single_point(self):
        """Test max drawdown calculation with single equity point."""
        runner = NautilusBacktestRunner()
        equity = [{"value": 10000.0}]
        result = runner._calculate_max_drawdown(equity)
        assert result == 0.0

    def test_calculate_max_drawdown_no_drawdown(self):
        """Test max drawdown calculation with only gains."""
        runner = NautilusBacktestRunner()
        equity = [
            {"value": 10000.0},
            {"value": 10500.0},
            {"value": 11000.0},
        ]
        result = runner._calculate_max_drawdown(equity)
        assert result == 0.0

    def test_calculate_max_drawdown_with_drawdown(self):
        """Test max drawdown calculation with actual drawdown."""
        runner = NautilusBacktestRunner()
        equity = [
            {"value": 10000.0},
            {"value": 12000.0},  # Peak
            {"value": 9600.0},  # 20% drawdown from peak
            {"value": 10000.0},
        ]
        result = runner._calculate_max_drawdown(equity)
        assert result == pytest.approx(-0.2, rel=1e-5)

    def test_calculate_win_rate_empty(self):
        """Test win rate calculation with no fills."""
        runner = NautilusBacktestRunner()
        result = runner._calculate_win_rate([])
        assert result == 0.0

    def test_calculate_win_rate_single_win(self):
        """Test win rate calculation with single winning trade."""
        runner = NautilusBacktestRunner()
        fills = [
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 110.0, "qty": 10.0},
        ]
        result = runner._calculate_win_rate(fills)
        assert result == 1.0

    def test_calculate_win_rate_single_loss(self):
        """Test win rate calculation with single losing trade."""
        runner = NautilusBacktestRunner()
        fills = [
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 90.0, "qty": 10.0},
        ]
        result = runner._calculate_win_rate(fills)
        assert result == 0.0

    def test_calculate_win_rate_mixed_trades(self):
        """Test win rate calculation with mixed winning and losing trades."""
        runner = NautilusBacktestRunner()
        fills = [
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 110.0, "qty": 10.0},  # Win
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 95.0, "qty": 10.0},  # Loss
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 105.0, "qty": 10.0},  # Win
        ]
        result = runner._calculate_win_rate(fills)
        assert result == pytest.approx(2.0 / 3.0, rel=1e-5)

    def test_extract_metrics_from_engine_with_equity(self):
        """Test metrics extraction with equity curve."""
        runner = NautilusBacktestRunner()

        # Mock engine without portfolio access
        class MockEngine:
            pass

        engine = MockEngine()
        equity = [
            {"value": 10000.0},
            {"value": 12000.0},
            {"value": 9600.0},
            {"value": 11000.0},
        ]
        fills = [
            {"side": "BUY", "price": 100.0, "qty": 10.0},
            {"side": "SELL", "price": 110.0, "qty": 10.0},
        ]

        metrics = runner._extract_metrics_from_engine(engine, equity, fills)

        assert "total_return" in metrics
        assert "max_drawdown" in metrics
        assert "win_rate" in metrics
        assert metrics["total_return"] == pytest.approx(0.1, rel=1e-5)  # 10% return
        assert metrics["max_drawdown"] == pytest.approx(-0.2, rel=1e-5)  # 20% drawdown
        assert metrics["win_rate"] == 1.0  # 100% win rate
