import unittest
from unittest.mock import patch

from app.strategies import MarketContext, RsiPullbackStrategy, Strategy
from app.strategy_executor import execute_rsi_pullback


class RsiPullbackStrategyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.strategy = RsiPullbackStrategy()

    def context(self, **data):
        return MarketContext(symbol="HK50", timeframe="1h", data=data)

    def assert_parity(self, **market_data):
        expected_signal, expected_reason = execute_rsi_pullback(market_data)
        decision = self.strategy.evaluate(self.context(**market_data))

        self.assertEqual(decision.strategy, "RSI Pullback")
        self.assertEqual(decision.signal, expected_signal)
        self.assertEqual(decision.reason, expected_reason)
        self.assertIsNone(decision.confidence)
        self.assertIsNone(decision.stop_loss)
        self.assertIsNone(decision.take_profit)
        self.assertEqual(dict(decision.metadata), {})

    def test_adapter_satisfies_strategy_protocol(self):
        self.assertIsInstance(self.strategy, Strategy)

    def test_bullish_pullback_buy_matches_existing_function(self):
        self.assert_parity(rsi=45, trend="Bullish", risk="Medium")

    def test_bearish_pullback_sell_matches_existing_function(self):
        self.assert_parity(rsi=55, trend="Bearish", risk="Low")

    def test_neutral_market_hold_matches_existing_function(self):
        self.assert_parity(rsi=50, trend="Neutral", risk="Medium")

    def test_high_risk_blocks_buy_and_matches_existing_reason(self):
        self.assert_parity(rsi=40, trend="Bullish", risk="High")

    def test_high_risk_blocks_sell_and_matches_existing_reason(self):
        self.assert_parity(rsi=60, trend="Bearish", risk="High")

    def test_comma_formatted_rsi_matches_existing_number_cleaning(self):
        self.assert_parity(rsi="45.0", trend="Bullish", risk="Low")

    def test_missing_values_match_existing_defaults(self):
        self.assert_parity()

    def test_adapter_delegates_to_existing_function(self):
        context = self.context(rsi=42, trend="Bullish", risk="Medium")

        with patch(
            "app.strategies.rsi_pullback.execute_rsi_pullback",
            return_value=("SELL", "delegated reason"),
        ) as legacy_execute:
            decision = self.strategy.evaluate(context)

        legacy_execute.assert_called_once_with(context.data)
        self.assertEqual(decision.signal, "SELL")
        self.assertEqual(decision.reason, "delegated reason")


if __name__ == "__main__":
    unittest.main()
