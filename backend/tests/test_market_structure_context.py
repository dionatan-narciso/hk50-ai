import unittest

from app.market_context import (
    calculate_signed_distance_percent,
    classify_directional_structure,
    classify_ma_alignment,
    classify_price_position,
    derive_market_structure_context,
)
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    MarketContext,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)


class MarketStructureContextTests(unittest.TestCase):
    def test_directional_structure_classification(self):
        cases = [
            ((110, 105, 100), "BULLISH_STACK"),
            ((90, 95, 100), "BEARISH_STACK"),
            ((105, 100, 110), "MIXED"),
            ((100, 100, 90), "MIXED"),
            ((0, 100, 90), "UNKNOWN"),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                self.assertEqual(classify_directional_structure(*values), expected)

    def test_price_position_classification(self):
        cases = [
            ((110, 105, 100), "ABOVE_BOTH"),
            ((90, 95, 100), "BELOW_BOTH"),
            ((102, 105, 100), "BETWEEN_MAS"),
            ((105, 105, 100), "AT_MA"),
            ((100, 105, 100), "AT_MA"),
            ((0, 105, 100), "UNKNOWN"),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                self.assertEqual(classify_price_position(*values), expected)

    def test_ma_alignment_classification(self):
        self.assertEqual(classify_ma_alignment(105, 100), "BULLISH")
        self.assertEqual(classify_ma_alignment(95, 100), "BEARISH")
        self.assertEqual(classify_ma_alignment(100, 100), "FLAT")
        self.assertEqual(classify_ma_alignment(0, 100), "UNKNOWN")

    def test_signed_distance_preserves_direction(self):
        self.assertAlmostEqual(calculate_signed_distance_percent(110, 100), 9.090909, places=5)
        self.assertAlmostEqual(calculate_signed_distance_percent(90, 100), -11.111111, places=5)
        self.assertIsNone(calculate_signed_distance_percent(0, 100))
        self.assertIsNone(calculate_signed_distance_percent(100, 0))

    def test_derived_structure_identifies_nearest_anchor(self):
        result = derive_market_structure_context(
            {"price": 110, "ma20": 108, "ma50": 100}
        )
        self.assertEqual(result.directional_structure, "BULLISH_STACK")
        self.assertEqual(result.price_position, "ABOVE_BOTH")
        self.assertEqual(result.ma_alignment, "BULLISH")
        self.assertEqual(result.nearest_anchor, "MA20")
        self.assertAlmostEqual(result.nearest_anchor_distance_percent, 1.818181, places=5)

    def test_nearest_anchor_tie_is_deterministically_ma20(self):
        result = derive_market_structure_context(
            {"price": 100, "ma20": 90, "ma50": 110}
        )
        self.assertEqual(result.nearest_anchor, "MA20")
        self.assertAlmostEqual(result.nearest_anchor_distance_percent, 10.0)

    def test_missing_values_produce_unknown_structure(self):
        result = derive_market_structure_context({})
        self.assertEqual(result.directional_structure, "UNKNOWN")
        self.assertEqual(result.price_position, "UNKNOWN")
        self.assertEqual(result.ma_alignment, "UNKNOWN")
        self.assertIsNone(result.distance_to_ma20_percent)
        self.assertIsNone(result.distance_to_ma50_percent)
        self.assertIsNone(result.nearest_anchor)
        self.assertIsNone(result.nearest_anchor_distance_percent)

    def test_structure_context_is_informational_only_for_all_strategies(self):
        data = {
            "price": 110,
            "ma20": 105,
            "ma50": 100,
            "rsi": 42,
            "trend": "Bullish",
            "risk": "Low",
            "confidence": 80,
        }
        structure = derive_market_structure_context(data)
        plain = MarketContext(symbol="HK50", timeframe="1h", data=data)
        enriched = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data=data,
            structure={
                "directional_structure": structure.directional_structure,
                "price_position": structure.price_position,
                "ma_alignment": structure.ma_alignment,
                "distance_to_ma20_percent": structure.distance_to_ma20_percent,
                "distance_to_ma50_percent": structure.distance_to_ma50_percent,
                "nearest_anchor": structure.nearest_anchor,
                "nearest_anchor_distance_percent": structure.nearest_anchor_distance_percent,
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
