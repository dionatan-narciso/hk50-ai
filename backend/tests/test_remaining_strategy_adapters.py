import ast
import unittest
from pathlib import Path

from app.strategies import MarketContext, Strategy
from app.strategies.breakout import BreakoutStrategy
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategy_executor import (
    execute_breakout,
    execute_ma_alignment,
    execute_trend_following,
)


class RemainingStrategyParityTests(unittest.TestCase):
    def make_context(self, **data):
        return MarketContext(symbol="HK50", timeframe="1h", data=data)

    def assert_parity(self, strategy, wrapper, **market_data):
        decision = strategy.evaluate(self.make_context(**market_data))
        wrapper_signal, wrapper_reason = wrapper(market_data)

        self.assertEqual(decision.strategy, strategy.name)
        self.assertEqual(decision.signal, wrapper_signal)
        self.assertEqual(decision.reason, wrapper_reason)

    def test_ma_alignment_buy_sell_hold_and_high_risk(self):
        strategy = MaAlignmentStrategy()
        cases = [
            {"price": 110, "ma20": 105, "ma50": 100, "risk": "Low"},
            {"price": 90, "ma20": 95, "ma50": 100, "risk": "Medium"},
            {"price": 105, "ma20": 100, "ma50": 102, "risk": "Low"},
            {"price": 110, "ma20": 105, "ma50": 100, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(strategy, execute_ma_alignment, **market_data)

    def test_ma_alignment_preserves_number_cleaning(self):
        self.assert_parity(
            MaAlignmentStrategy(),
            execute_ma_alignment,
            price="20,100",
            ma20="20,000",
            ma50="19,900",
            risk="Low",
        )

    def test_breakout_buy_sell_hold_and_high_risk(self):
        strategy = BreakoutStrategy()
        cases = [
            {"trend": "Bullish", "confidence": 70, "risk": "Low"},
            {"trend": "Bearish", "confidence": 85, "risk": "Medium"},
            {"trend": "Bullish", "confidence": 69.9, "risk": "Low"},
            {"trend": "Bullish", "confidence": 90, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(strategy, execute_breakout, **market_data)

    def test_breakout_preserves_number_cleaning_and_defaults(self):
        self.assert_parity(
            BreakoutStrategy(),
            execute_breakout,
            trend="Bullish",
            confidence="7,0",
            risk="Low",
        )
        self.assert_parity(BreakoutStrategy(), execute_breakout)

    def test_trend_following_buy_sell_hold_and_high_risk(self):
        strategy = TrendFollowingStrategy()
        cases = [
            {"trend": "Bullish", "rsi": 69.9, "risk": "Low"},
            {"trend": "Bearish", "rsi": 30.1, "risk": "Medium"},
            {"trend": "Bullish", "rsi": 70, "risk": "Low"},
            {"trend": "Bearish", "rsi": 50, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(strategy, execute_trend_following, **market_data)

    def test_trend_following_preserves_number_cleaning_and_defaults(self):
        self.assert_parity(
            TrendFollowingStrategy(),
            execute_trend_following,
            trend="Bullish",
            rsi="6,9",
            risk="Low",
        )
        self.assert_parity(TrendFollowingStrategy(), execute_trend_following)

    def test_all_strategies_satisfy_protocol(self):
        for strategy in (
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
        ):
            with self.subTest(strategy=strategy.name):
                self.assertIsInstance(strategy, Strategy)

    def test_plugins_own_rules_without_importing_executor(self):
        strategy_dir = Path(__file__).parents[1] / "app" / "strategies"
        for filename in ("ma_alignment.py", "breakout.py", "trend_following.py"):
            with self.subTest(filename=filename):
                tree = ast.parse((strategy_dir / filename).read_text(encoding="utf-8"))
                imports = [
                    node.module
                    for node in tree.body
                    if isinstance(node, ast.ImportFrom)
                ]
                self.assertNotIn("app.strategy_executor", imports)


if __name__ == "__main__":
    unittest.main()
