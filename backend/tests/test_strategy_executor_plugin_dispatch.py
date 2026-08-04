import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from app.strategies.contracts import StrategyDecision
from app.strategy_executor import (
    execute_strategy,
    resolve_registered_strategy_name,
)


CLEAR_REGIME = {
    "regime": "TRENDING",
    "volatility_regime": "NORMAL_VOLATILITY",
    "blocked_strategies": [],
    "reason": "Strategy allowed.",
}


class FakeStrategy:
    def __init__(self, name, signal="BUY", reason="Plugin decision."):
        self.name = name
        self.signal = signal
        self.reason = reason
        self.context = None

    def evaluate(self, context):
        self.context = context
        return StrategyDecision(
            strategy=self.name,
            signal=self.signal,
            reason=self.reason,
        )


class FakeRegistry:
    def __init__(self, strategy):
        self.strategy = strategy
        self.requested_name = None

    def get(self, name):
        self.requested_name = name
        return self.strategy


class StrategyExecutorPluginDispatchTests(unittest.TestCase):
    def test_existing_aliases_resolve_to_registry_names(self):
        cases = {
            "rsi pullback": "RSI Pullback",
            "rsi only": "RSI Pullback",
            "moving average": "MA Alignment",
            "ma alignment": "MA Alignment",
            "breakout": "Breakout",
            "trend following": "Trend Following",
            "unknown strategy": "Trend Following",
        }
        for source_name, expected in cases.items():
            with self.subTest(source_name=source_name):
                self.assertEqual(resolve_registered_strategy_name(source_name), expected)

    def test_registered_strategy_is_resolved_and_evaluated(self):
        strategy = FakeStrategy("Breakout", signal="SELL", reason="Plugin SELL.")
        registry = FakeRegistry(strategy)
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=CLEAR_REGIME),
            patch("app.strategy_executor.build_default_strategy_registry", return_value=registry),
        ):
            result = execute_strategy(
                {"strategy": "Breakout"},
                {"trend": "Bearish", "confidence": 80},
            )
        self.assertEqual(registry.requested_name, "Breakout")
        self.assertEqual(result["signal"], "SELL")
        self.assertEqual(result["strategy_reason"], "Plugin SELL.")
        self.assertEqual(strategy.context.symbol, "HK50")
        self.assertEqual(strategy.context.timeframe, "1h")

    def test_unknown_strategy_preserves_trend_following_fallback(self):
        strategy = FakeStrategy("Trend Following", signal="HOLD", reason="Fallback.")
        registry = FakeRegistry(strategy)
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=CLEAR_REGIME),
            patch("app.strategy_executor.build_default_strategy_registry", return_value=registry),
        ):
            result = execute_strategy("Completely Unknown", {"trend": "Neutral"})
        self.assertEqual(registry.requested_name, "Trend Following")
        self.assertEqual(result["strategy_reason"], "Fallback.")

    def test_regime_blocking_happens_before_registry_creation(self):
        blocked_regime = {
            "blocked_strategies": ["Breakout"],
            "reason": "Breakouts blocked.",
        }
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=blocked_regime),
            patch("app.strategy_executor.build_default_strategy_registry") as build_registry,
        ):
            result = execute_strategy("Breakout", {"trend": "Bullish"})
        build_registry.assert_not_called()
        self.assertEqual(result["signal"], "HOLD")
        self.assertEqual(
            result["strategy_reason"],
            "Strategy blocked by market regime. Breakouts blocked.",
        )

    def test_rsi_30_buy_behavior_is_preserved_without_registry(self):
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=CLEAR_REGIME),
            patch("app.strategy_executor.build_default_strategy_registry") as build_registry,
        ):
            result = execute_strategy("RSI < 30", {"rsi": 29, "risk": "Medium"})
        build_registry.assert_not_called()
        self.assertEqual(result["signal"], "BUY")
        self.assertEqual(result["strategy_reason"], "RSI < 30 strategy triggered BUY.")

    def test_rsi_30_hold_behavior_is_preserved_without_registry(self):
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=CLEAR_REGIME),
            patch("app.strategy_executor.build_default_strategy_registry") as build_registry,
        ):
            result = execute_strategy("RSI<30", {"rsi": 29, "risk": "High"})
        build_registry.assert_not_called()
        self.assertEqual(result["signal"], "HOLD")
        self.assertEqual(
            result["strategy_reason"],
            "RSI < 30 strategy found no valid setup.",
        )

    def test_response_contract_is_preserved(self):
        strategy = FakeStrategy("MA Alignment")
        registry = FakeRegistry(strategy)
        best_strategy = {"strategy": "MA Alignment", "source": "Research Memory"}
        with (
            patch("app.strategy_executor.detect_market_regime", return_value=CLEAR_REGIME),
            patch("app.strategy_executor.build_default_strategy_registry", return_value=registry),
        ):
            result = execute_strategy(best_strategy, {"price": 100})
        self.assertEqual(
            set(result),
            {"strategy_used", "signal", "strategy_reason", "market_regime"},
        )
        self.assertIs(result["strategy_used"], best_strategy)
        self.assertIs(result["market_regime"], CLEAR_REGIME)

    def test_registry_imports_are_top_level_after_cycle_removal(self):
        source_path = Path(__file__).parents[1] / "app" / "strategy_executor.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        top_level_imports = [
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertIn("app.strategies.default_registry", top_level_imports)
        self.assertIn("app.strategies.contracts", top_level_imports)


if __name__ == "__main__":
    unittest.main()
