import unittest
from dataclasses import FrozenInstanceError

from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    Rsi30Strategy,
    RsiPullbackStrategy,
    StrategyMetadata,
    StrategyRegistry,
    TrendFollowingStrategy,
    build_default_strategy_registry,
    build_execution_strategy_registry,
)


class StrategyMetadataCapabilityTests(unittest.TestCase):
    def test_metadata_defaults_match_current_platform_scope(self):
        metadata = StrategyMetadata()
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.supported_markets, ("HK50",))
        self.assertEqual(metadata.supported_timeframes, ("1h",))
        self.assertTrue(metadata.voting_eligible)
        self.assertTrue(metadata.supports("HK50", "1h"))
        self.assertFalse(metadata.supports("NAS100", "1h"))
        self.assertFalse(metadata.supports("HK50", "15m"))

    def test_metadata_is_immutable(self):
        metadata = StrategyMetadata()
        with self.assertRaises(FrozenInstanceError):
            metadata.version = "2.0.0"

    def test_metadata_rejects_empty_capabilities(self):
        with self.assertRaises(ValueError):
            StrategyMetadata(version=" ")
        with self.assertRaises(ValueError):
            StrategyMetadata(supported_markets=())
        with self.assertRaises(ValueError):
            StrategyMetadata(supported_timeframes=())
        with self.assertRaises(ValueError):
            StrategyMetadata(supported_markets=("",))
        with self.assertRaises(ValueError):
            StrategyMetadata(supported_timeframes=(" ",))

    def test_existing_voting_strategies_declare_current_capabilities(self):
        strategies = (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
        )
        for strategy in strategies:
            with self.subTest(strategy=strategy.name):
                self.assertEqual(strategy.metadata.version, "1.0.0")
                self.assertTrue(strategy.metadata.supports("HK50", "1h"))
                self.assertTrue(strategy.metadata.voting_eligible)

    def test_rsi_30_is_execution_only(self):
        strategy = Rsi30Strategy()
        self.assertTrue(strategy.metadata.supports("HK50", "1h"))
        self.assertFalse(strategy.metadata.voting_eligible)

    def test_registry_capability_queries_preserve_order(self):
        execution_registry = build_execution_strategy_registry()
        self.assertEqual(
            tuple(strategy.name for strategy in execution_registry.voting_eligible()),
            ("RSI Pullback", "MA Alignment", "Breakout", "Trend Following"),
        )
        self.assertEqual(
            tuple(
                strategy.name
                for strategy in execution_registry.compatible("HK50", "1h")
            ),
            (
                "RSI Pullback",
                "MA Alignment",
                "Breakout",
                "Trend Following",
                "RSI < 30",
            ),
        )
        self.assertEqual(
            tuple(
                strategy.name
                for strategy in execution_registry.compatible(
                    "HK50", "1h", voting_only=True
                )
            ),
            ("RSI Pullback", "MA Alignment", "Breakout", "Trend Following"),
        )

    def test_unsupported_context_returns_no_compatible_strategies(self):
        registry = build_execution_strategy_registry()
        self.assertEqual(registry.compatible("NAS100", "1h"), ())
        self.assertEqual(registry.compatible("HK50", "15m"), ())

    def test_default_voting_registry_remains_four_strategies(self):
        registry = build_default_strategy_registry()
        self.assertEqual(len(registry), 4)
        self.assertEqual(registry.all(), registry.voting_eligible())


if __name__ == "__main__":
    unittest.main()
