import ast
import unittest
from pathlib import Path

from app.strategies import MarketContext, RsiPullbackStrategy, Strategy
from app.strategy_executor import execute_rsi_pullback


class RsiPullbackStrategyTests(unittest.TestCase):
    def setUp(self):
        self.strategy = RsiPullbackStrategy()

    def context(self, **data):
        return MarketContext(symbol="HK50", timeframe="1h", data=data)

    def assert_parity(self, **market_data):
        decision = self.strategy.evaluate(self.context(**market_data))
        wrapper_signal, wrapper_reason = execute_rsi_pullback(market_data)

        self.assertEqual(decision.strategy, "RSI Pullback")
        self.assertEqual(decision.signal, wrapper_signal)
        self.assertEqual(decision.reason, wrapper_reason)
        self.assertIsNone(decision.confidence)
        self.assertIsNone(decision.stop_loss)
        self.assertIsNone(decision.take_profit)
        self.assertEqual(dict(decision.metadata), {})

    def test_strategy_satisfies_protocol(self):
        self.assertIsInstance(self.strategy, Strategy)

    def test_bullish_pullback_buy(self):
        self.assert_parity(rsi=45, trend="Bullish", risk="Medium")

    def test_bearish_pullback_sell(self):
        self.assert_parity(rsi=55, trend="Bearish", risk="Low")

    def test_neutral_market_hold(self):
        self.assert_parity(rsi=50, trend="Neutral", risk="Medium")

    def test_high_risk_blocks_buy(self):
        self.assert_parity(rsi=40, trend="Bullish", risk="High")

    def test_high_risk_blocks_sell(self):
        self.assert_parity(rsi=60, trend="Bearish", risk="High")

    def test_string_rsi_preserves_number_cleaning(self):
        self.assert_parity(rsi="45.0", trend="Bullish", risk="Low")

    def test_missing_values_preserve_defaults(self):
        self.assert_parity()

    def test_plugin_owns_rules_without_importing_executor(self):
        source_path = Path(__file__).parents[1] / "app" / "strategies" / "rsi_pullback.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = [
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertNotIn("app.strategy_executor", imports)


if __name__ == "__main__":
    unittest.main()
