import unittest
from dataclasses import FrozenInstanceError

from app.strategies import (
    MarketContext,
    Strategy,
    StrategyDecision,
    StrategyRegistry,
)


class ExampleStrategy:
    def __init__(self, name="Example"):
        self._name = name

    @property
    def name(self):
        return self._name

    def evaluate(self, context):
        return StrategyDecision(
            strategy=self.name,
            signal="buy",
            reason=f"RSI was {context.get('rsi')}",
        )


class StrategyPluginFoundationTests(unittest.TestCase):
    def test_market_context_preserves_existing_dictionary_access(self):
        context = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data={"rsi": 42, "risk": "Low"},
        )

        self.assertEqual(context.get("rsi"), 42)
        self.assertEqual(context.get("missing", "fallback"), "fallback")

    def test_market_context_identity_is_immutable(self):
        context = MarketContext(symbol="HK50", timeframe="1h", data={})

        with self.assertRaises(FrozenInstanceError):
            context.symbol = "NAS100"

    def test_strategy_decision_normalises_signal(self):
        decision = StrategyDecision(
            strategy="Example",
            signal="buy",
            reason="Example reason",
        )

        self.assertEqual(decision.signal, "BUY")

    def test_strategy_decision_rejects_invalid_signal(self):
        with self.assertRaises(ValueError):
            StrategyDecision(
                strategy="Example",
                signal="WAIT",
                reason="Unsupported signal",
            )

    def test_strategy_decision_validates_optional_confidence(self):
        StrategyDecision(
            strategy="Example",
            signal="HOLD",
            reason="Valid",
            confidence=0,
        )
        StrategyDecision(
            strategy="Example",
            signal="HOLD",
            reason="Valid",
            confidence=100,
        )

        with self.assertRaises(ValueError):
            StrategyDecision(
                strategy="Example",
                signal="HOLD",
                reason="Invalid",
                confidence=101,
            )

    def test_structural_strategy_protocol_accepts_plugin(self):
        strategy = ExampleStrategy()

        self.assertIsInstance(strategy, Strategy)
        self.assertEqual(
            strategy.evaluate(
                MarketContext(symbol="HK50", timeframe="1h", data={"rsi": 42})
            ).signal,
            "BUY",
        )

    def test_registry_preserves_registration_order(self):
        first = ExampleStrategy("First")
        second = ExampleStrategy("Second")
        registry = StrategyRegistry([first, second])

        self.assertEqual(registry.names(), ("First", "Second"))
        self.assertEqual(registry.all(), (first, second))
        self.assertEqual(len(registry), 2)

    def test_registry_rejects_duplicate_names(self):
        registry = StrategyRegistry([ExampleStrategy("Duplicate")])

        with self.assertRaises(ValueError):
            registry.register(ExampleStrategy("Duplicate"))

    def test_registry_rejects_empty_names(self):
        registry = StrategyRegistry()

        with self.assertRaises(ValueError):
            registry.register(ExampleStrategy("   "))

    def test_registry_lookup_and_membership(self):
        strategy = ExampleStrategy("Example")
        registry = StrategyRegistry([strategy])

        self.assertIn("Example", registry)
        self.assertIs(registry.get("Example"), strategy)

        with self.assertRaises(KeyError):
            registry.get("Missing")


if __name__ == "__main__":
    unittest.main()
