import unittest
from datetime import datetime, timezone

from app.market_context import (
    TimeframeSnapshot,
    build_enriched_market_context,
    build_market_context,
    derive_higher_timeframe_trend_context,
    derive_market_condition_context,
    derive_market_structure_context,
    derive_trading_session_context,
)
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)
from app.strategies.voting import run_registry_strategy_vote


class UnifiedMarketContextPipelineTests(unittest.TestCase):
    def setUp(self):
        self.primary_data = {
            "price": 20000,
            "ma20": 19900,
            "ma50": 19800,
            "rsi": 42,
            "trend": "Bullish",
            "risk": "Low",
            "confidence": 80,
            "atr_percent": 1.4,
        }
        self.primary = TimeframeSnapshot(
            symbol="HK50",
            timeframe="1h",
            data=self.primary_data,
            metadata={"source": "test"},
        )
        self.four_hour = TimeframeSnapshot(
            symbol="HK50",
            timeframe="4h",
            data={"trend": "Bullish", "rsi": 55},
        )
        self.daily = TimeframeSnapshot(
            symbol="HK50",
            timeframe="1d",
            data={"trend": "Bearish", "rsi": 48},
        )
        self.timestamp = datetime(2026, 8, 24, 14, 0, tzinfo=timezone.utc)

    def test_pipeline_preserves_primary_data_identity(self):
        context = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
        )
        self.assertIs(context.data, self.primary_data)
        self.assertEqual(context.get("rsi"), 42)

    def test_pipeline_preserves_higher_timeframe_namespaces(self):
        context = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
        )
        self.assertEqual(context.get_timeframe("4h")["trend"], "Bullish")
        self.assertEqual(context.get_timeframe("1d")["trend"], "Bearish")

    def test_pipeline_matches_independent_derivations(self):
        base = build_market_context(self.primary, self.four_hour, self.daily)
        expected_trend = derive_higher_timeframe_trend_context(base)
        expected_session = derive_trading_session_context(self.timestamp)
        expected_condition = derive_market_condition_context(self.primary_data)
        expected_structure = derive_market_structure_context(self.primary_data)

        context = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
        )

        self.assertEqual(
            context.features["higher_timeframe_trend"]["agreement"],
            expected_trend.agreement,
        )
        self.assertEqual(
            context.features["market_condition"]["volatility"],
            expected_condition.volatility,
        )
        self.assertEqual(context.session["label"], expected_session.label)
        self.assertEqual(
            context.structure["directional_structure"],
            expected_structure.directional_structure,
        )

    def test_pipeline_keeps_enrichment_out_of_primary_data(self):
        context = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
        )
        self.assertNotIn("higher_timeframe_trend", context.data)
        self.assertNotIn("market_condition", context.data)
        self.assertNotIn("directional_structure", context.data)
        self.assertNotIn("session", context.data)

    def test_pipeline_preserves_metadata_and_regime(self):
        context = build_enriched_market_context(
            self.primary,
            timestamp=self.timestamp,
            metadata={"run_id": "abc"},
            regime={"market_regime": "TRENDING"},
        )
        self.assertEqual(context.metadata["source"], "test")
        self.assertEqual(context.metadata["run_id"], "abc")
        self.assertEqual(context.regime["market_regime"], "TRENDING")

    def test_pipeline_rejects_naive_timestamp(self):
        with self.assertRaises(ValueError):
            build_enriched_market_context(
                self.primary,
                timestamp=datetime(2026, 8, 24, 14, 0),
            )

    def test_all_strategy_decisions_match_plain_context(self):
        plain = build_market_context(self.primary, self.four_hour, self.daily)
        enriched = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
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

    def test_registry_voting_remains_identical(self):
        plain_vote = run_registry_strategy_vote(self.primary_data)
        enriched = build_enriched_market_context(
            self.primary,
            self.four_hour,
            self.daily,
            timestamp=self.timestamp,
        )
        enriched_vote = run_registry_strategy_vote(enriched.data)
        self.assertEqual(plain_vote, enriched_vote)


if __name__ == "__main__":
    unittest.main()
