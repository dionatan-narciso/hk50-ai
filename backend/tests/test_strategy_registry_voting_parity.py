import unittest

from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.default_registry import build_default_strategy_registry
from app.strategies.registry import StrategyRegistry
from app.strategies.voting import run_registry_strategy_vote
from app.strategy_voting_engine import run_strategy_vote


class RecordingStrategy:
    def __init__(self, name, signal, seen_contexts):
        self._name = name
        self._signal = signal
        self._seen_contexts = seen_contexts

    @property
    def name(self):
        return self._name

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        self._seen_contexts.append(context)
        return StrategyDecision(
            strategy=self.name,
            signal=self._signal,
            reason=f"{self.name} reason",
        )


class DefaultStrategyRegistryTests(unittest.TestCase):
    def test_default_registry_preserves_existing_voting_order(self):
        registry = build_default_strategy_registry()

        self.assertEqual(
            registry.names(),
            (
                "RSI Pullback",
                "MA Alignment",
                "Breakout",
                "Trend Following",
            ),
        )

    def test_default_registry_factory_returns_fresh_instances(self):
        first = build_default_strategy_registry()
        second = build_default_strategy_registry()

        self.assertIsNot(first, second)
        self.assertEqual(first.names(), second.names())
        for first_strategy, second_strategy in zip(first.all(), second.all()):
            self.assertIsNot(first_strategy, second_strategy)


class RegistryStrategyVotingParityTests(unittest.TestCase):
    def test_registry_voting_matches_legacy_engine_across_market_scenarios(self):
        scenarios = [
            {
                "price": 110,
                "ma20": 105,
                "ma50": 100,
                "rsi": 40,
                "trend": "Bullish",
                "confidence": 75,
                "risk": "Low",
            },
            {
                "price": 90,
                "ma20": 95,
                "ma50": 100,
                "rsi": 60,
                "trend": "Bearish",
                "confidence": 75,
                "risk": "Medium",
            },
            {
                "price": 100,
                "ma20": 100,
                "ma50": 100,
                "rsi": 50,
                "trend": "Neutral",
                "confidence": 50,
                "risk": "Medium",
            },
            {
                "price": "1,110",
                "ma20": "1,105",
                "ma50": "1,100",
                "rsi": "40",
                "trend": "Bullish",
                "confidence": "75",
                "risk": "Low",
            },
            {
                "price": 110,
                "ma20": 105,
                "ma50": 100,
                "rsi": 40,
                "trend": "Bullish",
                "confidence": 90,
                "risk": "High",
            },
            {},
        ]

        for market_data in scenarios:
            with self.subTest(market_data=market_data):
                self.assertEqual(
                    run_registry_strategy_vote(market_data),
                    run_strategy_vote(market_data),
                )

    def test_custom_registry_preserves_vote_counting_and_response_shape(self):
        seen_contexts = []
        registry = StrategyRegistry(
            [
                RecordingStrategy("One", "BUY", seen_contexts),
                RecordingStrategy("Two", "BUY", seen_contexts),
                RecordingStrategy("Three", "SELL", seen_contexts),
                RecordingStrategy("Four", "HOLD", seen_contexts),
            ]
        )

        result = run_registry_strategy_vote(
            {"price": 123},
            registry,
            symbol="NAS100",
            timeframe="15m",
        )

        self.assertEqual(result["final_vote"], "BUY")
        self.assertEqual(result["vote_strength"], 2)
        self.assertEqual(result["buy_votes"], 2)
        self.assertEqual(result["sell_votes"], 1)
        self.assertEqual(result["hold_votes"], 1)
        self.assertEqual(result["total_votes"], 4)
        self.assertEqual(
            set(result),
            {
                "votes",
                "buy_votes",
                "sell_votes",
                "hold_votes",
                "final_vote",
                "vote_strength",
                "total_votes",
            },
        )

        self.assertEqual(len(seen_contexts), 4)
        for context in seen_contexts:
            self.assertEqual(context.symbol, "NAS100")
            self.assertEqual(context.timeframe, "15m")
            self.assertEqual(context.get("price"), 123)

    def test_explicit_empty_registry_is_not_replaced_by_default(self):
        result = run_registry_strategy_vote({}, StrategyRegistry())

        self.assertEqual(
            result,
            {
                "votes": [],
                "buy_votes": 0,
                "sell_votes": 0,
                "hold_votes": 0,
                "final_vote": "HOLD",
                "vote_strength": 0,
                "total_votes": 0,
            },
        )

    def test_hold_vote_strength_preserves_existing_hold_count_rule(self):
        registry = StrategyRegistry(
            [
                RecordingStrategy("One", "BUY", []),
                RecordingStrategy("Two", "SELL", []),
                RecordingStrategy("Three", "HOLD", []),
                RecordingStrategy("Four", "HOLD", []),
            ]
        )

        result = run_registry_strategy_vote({}, registry)

        self.assertEqual(result["final_vote"], "HOLD")
        self.assertEqual(result["vote_strength"], 2)


if __name__ == "__main__":
    unittest.main()
