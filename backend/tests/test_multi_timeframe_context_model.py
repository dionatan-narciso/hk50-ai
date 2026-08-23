import unittest

from app.market_context import TimeframeSnapshot, build_market_context
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)


class MultiTimeframeContextModelTests(unittest.TestCase):
    def test_snapshot_requires_symbol_and_timeframe(self):
        with self.assertRaises(ValueError):
            TimeframeSnapshot(symbol="", timeframe="1h", data={})
        with self.assertRaises(ValueError):
            TimeframeSnapshot(symbol="HK50", timeframe="", data={})

    def test_builder_preserves_primary_mapping_and_identity(self):
        primary_data = {"rsi": 42, "trend": "Bullish", "risk": "Low"}
        primary = TimeframeSnapshot("HK50", "1h", primary_data)

        context = build_market_context(primary)

        self.assertIs(context.data, primary_data)
        self.assertEqual(context.symbol, "HK50")
        self.assertEqual(context.timeframe, "1h")
        self.assertEqual(context.get("rsi"), 42)

    def test_builder_attaches_4h_and_daily_without_flattening(self):
        primary = TimeframeSnapshot("HK50", "1h", {"rsi": 42})
        four_hour = TimeframeSnapshot("HK50", "4h", {"trend": "Bullish", "rsi": 55})
        daily = TimeframeSnapshot("HK50", "1d", {"trend": "Bearish", "rsi": 60})

        context = build_market_context(primary, four_hour, daily)

        self.assertEqual(context.get_timeframe("4h")["trend"], "Bullish")
        self.assertEqual(context.get_timeframe("1d")["trend"], "Bearish")
        self.assertNotIn("trend", context.data)

    def test_builder_rejects_symbol_mismatch(self):
        primary = TimeframeSnapshot("HK50", "1h", {})
        other_market = TimeframeSnapshot("NAS100", "4h", {})

        with self.assertRaisesRegex(ValueError, "must match primary symbol"):
            build_market_context(primary, other_market)

    def test_builder_rejects_duplicate_primary_timeframe(self):
        primary = TimeframeSnapshot("HK50", "1h", {})
        duplicate = TimeframeSnapshot("HK50", "1h", {"rsi": 50})

        with self.assertRaisesRegex(ValueError, "duplicates primary timeframe"):
            build_market_context(primary, duplicate)

    def test_builder_rejects_duplicate_higher_timeframe(self):
        primary = TimeframeSnapshot("HK50", "1h", {})
        first = TimeframeSnapshot("HK50", "4h", {})
        second = TimeframeSnapshot("HK50", "4h", {"rsi": 50})

        with self.assertRaisesRegex(ValueError, "Duplicate higher-timeframe"):
            build_market_context(primary, first, second)

    def test_builder_merges_primary_and_context_metadata(self):
        primary = TimeframeSnapshot(
            "HK50",
            "1h",
            {},
            metadata={"source": "replay", "shared": "primary"},
        )

        context = build_market_context(
            primary,
            metadata={"shared": "context", "run_id": "abc"},
        )

        self.assertEqual(
            dict(context.metadata),
            {"source": "replay", "shared": "context", "run_id": "abc"},
        )

    def test_builder_carries_enrichment_namespaces(self):
        primary = TimeframeSnapshot("HK50", "1h", {})
        context = build_market_context(
            primary,
            regime={"regime": "TRENDING"},
            session={"name": "ASIA"},
            structure={"support": 24000},
            features={"trend_strength": 0.8},
        )

        self.assertEqual(context.regime["regime"], "TRENDING")
        self.assertEqual(context.session["name"], "ASIA")
        self.assertEqual(context.structure["support"], 24000)
        self.assertEqual(context.get_feature("trend_strength"), 0.8)

    def test_higher_timeframes_do_not_change_existing_strategy_decisions(self):
        primary_data = {
            "rsi": 42,
            "trend": "Bullish",
            "risk": "Low",
            "price": 20100,
            "ma20": 20000,
            "ma50": 19900,
            "confidence": 75,
        }
        primary = TimeframeSnapshot("HK50", "1h", primary_data)
        conflicting_four_hour = TimeframeSnapshot(
            "HK50",
            "4h",
            {
                "rsi": 80,
                "trend": "Bearish",
                "risk": "High",
                "price": 19000,
                "ma20": 19500,
                "ma50": 20000,
                "confidence": 10,
            },
        )

        plain = build_market_context(primary)
        enriched = build_market_context(primary, conflicting_four_hour)

        for strategy in (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        ):
            with self.subTest(strategy=strategy.name):
                self.assertEqual(strategy.evaluate(enriched), strategy.evaluate(plain))


if __name__ == "__main__":
    unittest.main()
