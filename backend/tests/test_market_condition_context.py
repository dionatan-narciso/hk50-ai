import unittest

from app.market_context import (
    calculate_ma_separation_percent,
    classify_trend_strength,
    classify_volatility,
    derive_market_condition_context,
)
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    MarketContext,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)


class MarketConditionContextTests(unittest.TestCase):
    def test_volatility_reuses_existing_regime_thresholds(self):
        cases = [
            (0, "LOW_VOLATILITY"),
            (1, "LOW_VOLATILITY"),
            (1.01, "NORMAL_VOLATILITY"),
            (1.99, "NORMAL_VOLATILITY"),
            (2, "HIGH_VOLATILITY"),
            (3.5, "HIGH_VOLATILITY"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_volatility(value), expected)

    def test_volatility_preserves_existing_number_cleaning(self):
        self.assertEqual(classify_volatility("2.5"), "HIGH_VOLATILITY")
        self.assertEqual(classify_volatility("bad"), "LOW_VOLATILITY")

    def test_ma_separation_percent_is_price_relative(self):
        result = calculate_ma_separation_percent(
            {"price": 200, "ma20": 202, "ma50": 200}
        )
        self.assertAlmostEqual(result, 1.0)

    def test_ma_separation_requires_positive_price_and_mas(self):
        self.assertIsNone(calculate_ma_separation_percent({}))
        self.assertIsNone(
            calculate_ma_separation_percent({"price": 100, "ma20": 0, "ma50": 99})
        )

    def test_trend_strength_boundaries(self):
        cases = [
            (None, "UNKNOWN"),
            (0.0, "FLAT"),
            (0.099, "FLAT"),
            (0.1, "WEAK"),
            (0.499, "WEAK"),
            (0.5, "MODERATE"),
            (0.999, "MODERATE"),
            (1.0, "STRONG"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_trend_strength(value), expected)

    def test_derived_context_preserves_raw_trend(self):
        result = derive_market_condition_context(
            {
                "price": 20000,
                "ma20": 20200,
                "ma50": 19900,
                "atr_percent": 2.2,
                "trend": "Bullish",
            }
        )
        self.assertEqual(result.volatility, "HIGH_VOLATILITY")
        self.assertEqual(result.trend_strength, "STRONG")
        self.assertAlmostEqual(result.ma_separation_percent, 1.5)
        self.assertEqual(result.trend, "Bullish")

    def test_condition_context_is_informational_only_for_all_strategies(self):
        data = {
            "price": 20000,
            "ma20": 20200,
            "ma50": 19900,
            "atr_percent": 2.5,
            "rsi": 42,
            "trend": "Bullish",
            "risk": "Low",
            "confidence": 80,
        }
        condition = derive_market_condition_context(data)
        plain = MarketContext(symbol="HK50", timeframe="1h", data=data)
        enriched = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data=data,
            features={
                "volatility": condition.volatility,
                "trend_strength": condition.trend_strength,
                "ma_separation_percent": condition.ma_separation_percent,
            },
        )

        for strategy in (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        ):
            with self.subTest(strategy=strategy.name):
                self.assertEqual(strategy.evaluate(plain), strategy.evaluate(enriched))


if __name__ == "__main__":
    unittest.main()
