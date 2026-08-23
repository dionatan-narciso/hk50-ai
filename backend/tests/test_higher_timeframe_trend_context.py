import unittest

from app.market_context import (
    TimeframeSnapshot,
    build_market_context,
    derive_higher_timeframe_trend_context,
    normalize_trend,
)
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)


class HigherTimeframeTrendContextTests(unittest.TestCase):
    def build_context(self, primary_data=None, *higher):
        primary = TimeframeSnapshot(
            symbol="HK50",
            timeframe="1h",
            data=primary_data or {
                "rsi": 40,
                "trend": "Bullish",
                "risk": "Low",
                "price": 110,
                "ma20": 105,
                "ma50": 100,
                "confidence": 75,
            },
        )
        return build_market_context(primary, *higher)

    def test_normalize_trend_preserves_known_labels_case_insensitively(self):
        self.assertEqual(normalize_trend("Bullish"), "Bullish")
        self.assertEqual(normalize_trend(" bullish "), "Bullish")
        self.assertEqual(normalize_trend("BEARISH"), "Bearish")
        self.assertEqual(normalize_trend("Neutral"), "Neutral")

    def test_unknown_and_missing_trends_are_neutral_not_inferred(self):
        self.assertEqual(normalize_trend(None), "Neutral")
        self.assertEqual(normalize_trend("Sideways"), "Neutral")
        self.assertEqual(normalize_trend(""), "Neutral")

    def test_bullish_higher_timeframes_are_aligned(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bullish"}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Bullish"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(summary.trends, {"4h": "Bullish", "1d": "Bullish"})
        self.assertEqual(summary.agreement, "ALIGNED")
        self.assertEqual(summary.aligned_direction, "Bullish")
        self.assertEqual(summary.bullish_count, 2)
        self.assertEqual(summary.bearish_count, 0)
        self.assertEqual(summary.neutral_count, 0)

    def test_bearish_higher_timeframes_are_aligned(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bearish"}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Bearish"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(summary.agreement, "ALIGNED")
        self.assertEqual(summary.aligned_direction, "Bearish")
        self.assertEqual(summary.bearish_count, 2)

    def test_opposing_directional_timeframes_are_conflicting(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bullish"}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Bearish"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(summary.agreement, "CONFLICTING")
        self.assertIsNone(summary.aligned_direction)
        self.assertEqual(summary.bullish_count, 1)
        self.assertEqual(summary.bearish_count, 1)

    def test_neutral_timeframe_does_not_create_false_conflict(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bullish"}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Neutral"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(summary.agreement, "ALIGNED")
        self.assertEqual(summary.aligned_direction, "Bullish")
        self.assertEqual(summary.neutral_count, 1)

    def test_all_neutral_timeframes_are_reported_as_neutral(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Sideways"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(summary.agreement, "NEUTRAL")
        self.assertIsNone(summary.aligned_direction)
        self.assertEqual(summary.neutral_count, 2)

    def test_no_higher_timeframes_has_explicit_status(self):
        summary = derive_higher_timeframe_trend_context(self.build_context())

        self.assertEqual(summary.trends, {})
        self.assertEqual(summary.agreement, "NO_HIGHER_TIMEFRAMES")
        self.assertIsNone(summary.aligned_direction)

    def test_timeframe_order_is_preserved(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bullish"}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Bullish"}),
        )

        summary = derive_higher_timeframe_trend_context(context)

        self.assertEqual(tuple(summary.trends), ("4h", "1d"))

    def test_deriving_summary_does_not_change_strategy_decisions(self):
        context = self.build_context(
            None,
            TimeframeSnapshot("HK50", "4h", {"trend": "Bearish", "rsi": 80}),
            TimeframeSnapshot("HK50", "1d", {"trend": "Bearish", "rsi": 80}),
        )
        strategies = (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        )

        before = [strategy.evaluate(context) for strategy in strategies]
        summary = derive_higher_timeframe_trend_context(context)
        after = [strategy.evaluate(context) for strategy in strategies]

        self.assertEqual(summary.aligned_direction, "Bearish")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
