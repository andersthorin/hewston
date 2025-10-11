import importlib

from backend.strategies.strategy_factory import StrategyFactory, StrategyRegistry


def test_strategy_factory_builds_momentum():
    reg = StrategyRegistry()
    dotted = reg.get("momentum_v1")
    # Dynamically import and instantiate to ensure import path is valid
    module_name, class_name = dotted.rsplit(":", 1)
    module = importlib.import_module(module_name)
    StrategyClass = getattr(module, class_name)
    s = StrategyClass("AAPL.XNAS", window=10)
    assert s is not None


def test_strategy_factory_builds_rsi_mr():
    reg = StrategyRegistry()
    dotted = reg.get("rsi_mean_reversion_v1")
    module_name, class_name = dotted.rsplit(":", 1)
    module = importlib.import_module(module_name)
    StrategyClass = getattr(module, class_name)
    s = StrategyClass("AAPL.XNAS", rsi_period=7)
    assert s is not None


def test_strategy_factory_builds_donchian():
    reg = StrategyRegistry()
    dotted = reg.get("donchian_breakout_v1")
    module_name, class_name = dotted.rsplit(":", 1)
    module = importlib.import_module(module_name)
    StrategyClass = getattr(module, class_name)
    s = StrategyClass("AAPL.XNAS", window=15)
    assert s is not None

