import unittest
from unittest.mock import patch

from app.strategies import MarketContext, Strategy
from app.strategies.breakout import BreakoutStrategy
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategy_executor import (
    execute_breakout,
    execute_ma_alignment,
    execute_trend_following,
)


class RemainingStrategyAdapterParityTests(unittest.TestCase):
    def make_context(self, **data):
        return MarketContext(symbol="HK50", timeframe="1h", data=data)

    def assert_parity(self, adapter, legacy_function, **market_data):
        expected_signal, expected_reason = legacy_function(market_data)
        decision = adapter.evaluate(self.make_context(**market_data))

        self.assertEqual(decision.strategy, adapter.name)
        self.assertEqual(decision.signal, expected_signal)
        self.assertEqual(decision.reason, expected_reason)

    def test_ma_alignment_buy_sell_hold_and_high_risk_parity(self):
        adapter = MaAlignmentStrategy()
        cases = [
            {"price": 110, "ma20": 105, "ma50": 100, "risk": "Low"},
            {"price": 90, "ma20": 95, "ma50": 100, "risk": "Medium"},
            {"price": 105, "ma20": 100, "ma50": 102, "risk": "Low"},
            {"price": 110, "ma20": 105, "ma50": 100, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(adapter, execute_ma_alignment, **market_data)

    def test_ma_alignment_preserves_number_cleaning(self):
        self.assert_parity(
            MaAlignmentStrategy(),
            execute_ma_alignment,
            price="20,100",
            ma20="20,000",
            ma50="19,900",
            risk="Low",
        )

    def test_breakout_buy_sell_hold_and_high_risk_parity(self):
        adapter = BreakoutStrategy()
        cases = [
            {"trend": "Bullish", "confidence": 70, "risk": "Low"},
            {"trend": "Bearish", "confidence": 85, "risk": "Medium"},
            {"trend": "Bullish", "confidence": 69.9, "risk": "Low"},
            {"trend": "Bullish", "confidence": 90, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(adapter, execute_breakout, **market_data)

    def test_breakout_preserves_number_cleaning_and_defaults(self):
        self.assert_parity(
            BreakoutStrategy(),
            execute_breakout,
            trend="Bullish",
            confidence="7,0",
            risk="Low",
        )
        self.assert_parity(BreakoutStrategy(), execute_breakout)

    def test_trend_following_buy_sell_hold_and_high_risk_parity(self):
        adapter = TrendFollowingStrategy()
        cases = [
            {"trend": "Bullish", "rsi": 69.9, "risk": "Low"},
            {"trend": "Bearish", "rsi": 30.1, "risk": "Medium"},
            {"trend": "Bullish", "rsi": 70, "risk": "Low"},
            {"trend": "Bearish", "rsi": 50, "risk": "High"},
        ]
        for market_data in cases:
            with self.subTest(market_data=market_data):
                self.assert_parity(adapter, execute_trend_following, **market_data)

    def test_trend_following_preserves_number_cleaning_and_defaults(self):
        self.assert_parity(
            TrendFollowingStrategy(),
            execute_trend_following,
            trend="Bullish",
            rsi="6,9",
            risk="Low",
        )
        self.assert_parity(TrendFollowingStrategy(), execute_trend_following)

    def test_all_adapters_satisfy_strategy_protocol(self):
        for adapter in (
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
        ):
            with self.subTest(strategy=adapter.name):
                self.assertIsInstance(adapter, Strategy)

    def test_each_adapter_delegates_to_legacy_function(self):
        cases = [
            (
                "app.strategies.ma_alignment.execute_ma_alignment",
                MaAlignmentStrategy(),
            ),
            (
                "app.strategies.breakout.execute_breakout",
                BreakoutStrategy(),
            ),
            (
                "app.strategies.trend_following.execute_trend_following",
                TrendFollowingStrategy(),
            ),
        ]

        for target, adapter in cases:
            with self.subTest(strategy=adapter.name), patch(
                target,
                return_value=("SELL", "delegated"),
            ) as mocked:
                context = self.make_context(example=1)
                decision = adapter.evaluate(context)

                mocked.assert_called_once_with(context.data)
                self.assertEqual(decision.signal, "SELL")
                self.assertEqual(decision.reason, "delegated")


if __name__ == "__main__":
    unittest.main()
