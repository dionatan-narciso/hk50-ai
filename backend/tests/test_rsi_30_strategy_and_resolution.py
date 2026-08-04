import ast
import unittest
from pathlib import Path

from app.strategies import (
    MarketContext,
    Rsi30Strategy,
    Strategy,
    build_default_strategy_registry,
    build_execution_strategy_registry,
)
from app.strategies.resolution import (
    extract_strategy_name,
    is_strategy_blocked_by_regime,
    resolve_registered_strategy_name,
)


class Rsi30StrategyAndResolutionTests(unittest.TestCase):
    def setUp(self):
        self.strategy = Rsi30Strategy()

    def context(self, **data):
        return MarketContext(symbol="HK50", timeframe="1h", data=data)

    def test_rsi_30_plugin_satisfies_strategy_protocol(self):
        self.assertIsInstance(self.strategy, Strategy)

    def test_rsi_30_buy_boundary_and_reason_are_preserved(self):
        decision = self.strategy.evaluate(self.context(rsi=29.999, risk="Medium"))
        self.assertEqual(decision.signal, "BUY")
        self.assertEqual(decision.reason, "RSI < 30 strategy triggered BUY.")

    def test_rsi_30_holds_at_30_and_for_high_risk(self):
        for market_data in (
            {"rsi": 30, "risk": "Low"},
            {"rsi": 29, "risk": "High"},
        ):
            with self.subTest(market_data=market_data):
                decision = self.strategy.evaluate(self.context(**market_data))
                self.assertEqual(decision.signal, "HOLD")
                self.assertEqual(
                    decision.reason,
                    "RSI < 30 strategy found no valid setup.",
                )

    def test_rsi_30_preserves_number_cleaning_and_defaults(self):
        self.assertEqual(
            self.strategy.evaluate(self.context(rsi="2,9", risk="Low")).signal,
            "BUY",
        )
        self.assertEqual(self.strategy.evaluate(self.context()).signal, "HOLD")

    def test_voting_registry_remains_original_four_strategies(self):
        self.assertEqual(
            build_default_strategy_registry().names(),
            (
                "RSI Pullback",
                "MA Alignment",
                "Breakout",
                "Trend Following",
            ),
        )

    def test_execution_registry_adds_rsi_30_without_reordering_voters(self):
        self.assertEqual(
            build_execution_strategy_registry().names(),
            (
                "RSI Pullback",
                "MA Alignment",
                "Breakout",
                "Trend Following",
                "RSI < 30",
            ),
        )

    def test_strategy_name_extraction_preserves_existing_contract(self):
        self.assertEqual(extract_strategy_name({"strategy": "Breakout"}), "breakout")
        self.assertEqual(extract_strategy_name("Trend Following"), "trend following")
        self.assertEqual(extract_strategy_name({}), "")

    def test_alias_resolution_preserves_precedence_and_fallback(self):
        cases = {
            "rsi<30": "RSI < 30",
            "rsi < 30 parameter test": "RSI < 30",
            "rsi pullback": "RSI Pullback",
            "moving average alignment": "MA Alignment",
            "breakout test": "Breakout",
            "trend system": "Trend Following",
            "unknown": "Trend Following",
        }
        for source_name, expected in cases.items():
            with self.subTest(source_name=source_name):
                self.assertEqual(resolve_registered_strategy_name(source_name), expected)

    def test_regime_blocking_aliases_are_preserved(self):
        cases = [
            ("rsi<30", ["RSI < 30"]),
            ("rsi pullback", ["RSI Pullback"]),
            ("moving average", ["MA Alignment"]),
            ("breakout", ["Breakout"]),
            ("trend", ["Trend Following"]),
        ]
        for strategy_name, blocked in cases:
            with self.subTest(strategy_name=strategy_name):
                self.assertTrue(
                    is_strategy_blocked_by_regime(
                        strategy_name,
                        {"blocked_strategies": blocked},
                    )
                )
        self.assertFalse(
            is_strategy_blocked_by_regime(
                "breakout",
                {"blocked_strategies": []},
            )
        )

    def test_executor_contains_no_rsi_30_threshold_rule(self):
        source_path = Path(__file__).parents[1] / "app" / "strategy_executor.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn('market_data.get("rsi")', source)
        self.assertNotIn("rsi < 30", source)
        self.assertTrue(any(isinstance(node, ast.ImportFrom) for node in tree.body))


if __name__ == "__main__":
    unittest.main()
