import unittest
from unittest.mock import patch

from app.strategies import (
    StrategyDecision,
    StrategyMetadata,
    StrategyRegistry,
    build_default_strategy_registry,
    build_execution_strategy_registry,
    validate_strategy_registry,
)


class FakeStrategy:
    def __init__(
        self,
        name,
        *,
        markets=("HK50",),
        timeframes=("1h",),
        voting_eligible=True,
    ):
        self.name = name
        self.metadata = StrategyMetadata(
            version="1.0.0",
            supported_markets=frozenset(markets),
            supported_timeframes=frozenset(timeframes),
            voting_eligible=voting_eligible,
        )

    def evaluate(self, context):
        return StrategyDecision(
            strategy=self.name,
            signal="HOLD",
            reason="Fake strategy.",
        )


class StrategyRegistryValidationTests(unittest.TestCase):
    def test_valid_registry_is_returned_unchanged(self):
        registry = StrategyRegistry([FakeStrategy("Valid")])

        result = validate_strategy_registry(
            registry,
            symbol="HK50",
            timeframe="1h",
            require_voting_eligible=True,
        )

        self.assertIs(result, registry)

    def test_incompatible_market_is_rejected_with_strategy_name(self):
        registry = StrategyRegistry(
            [FakeStrategy("Gold Only", markets=("GOLD",))]
        )

        with self.assertRaisesRegex(
            ValueError,
            r"incompatible with HK50/1h: Gold Only",
        ):
            validate_strategy_registry(
                registry,
                symbol="HK50",
                timeframe="1h",
            )

    def test_incompatible_timeframe_is_rejected(self):
        registry = StrategyRegistry(
            [FakeStrategy("Daily Only", timeframes=("1d",))]
        )

        with self.assertRaisesRegex(ValueError, "Daily Only"):
            validate_strategy_registry(
                registry,
                symbol="HK50",
                timeframe="1h",
            )

    def test_all_incompatible_names_are_reported_in_order(self):
        registry = StrategyRegistry(
            [
                FakeStrategy("First", markets=("NAS100",)),
                FakeStrategy("Second", timeframes=("4h",)),
            ]
        )

        with self.assertRaisesRegex(ValueError, "First, Second"):
            validate_strategy_registry(
                registry,
                symbol="HK50",
                timeframe="1h",
            )

    def test_non_voting_strategy_is_allowed_in_execution_registry(self):
        registry = StrategyRegistry(
            [FakeStrategy("Execution Only", voting_eligible=False)]
        )

        self.assertIs(
            validate_strategy_registry(
                registry,
                symbol="HK50",
                timeframe="1h",
            ),
            registry,
        )

    def test_non_voting_strategy_is_rejected_from_voting_registry(self):
        registry = StrategyRegistry(
            [FakeStrategy("Execution Only", voting_eligible=False)]
        )

        with self.assertRaisesRegex(
            ValueError,
            "Voting registry contains non-voting strategies: Execution Only",
        ):
            validate_strategy_registry(
                registry,
                symbol="HK50",
                timeframe="1h",
                require_voting_eligible=True,
            )

    def test_default_voting_registry_is_validated(self):
        with patch(
            "app.strategies.default_registry.validate_strategy_registry",
            wraps=validate_strategy_registry,
        ) as validator:
            registry = build_default_strategy_registry()

        validator.assert_called_once_with(
            registry,
            symbol="HK50",
            timeframe="1h",
            require_voting_eligible=True,
        )
        self.assertEqual(len(registry), 4)

    def test_execution_registry_is_validated_without_voting_requirement(self):
        with patch(
            "app.strategies.default_registry.validate_strategy_registry",
            wraps=validate_strategy_registry,
        ) as validator:
            registry = build_execution_strategy_registry()

        validator.assert_called_once_with(
            registry,
            symbol="HK50",
            timeframe="1h",
        )
        self.assertEqual(len(registry), 5)
        self.assertIn("RSI < 30", registry)


if __name__ == "__main__":
    unittest.main()
