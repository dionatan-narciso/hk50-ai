import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from app import strategy_voting_engine


class StrategyVotingEngineWiringTests(unittest.TestCase):
    def test_run_strategy_vote_delegates_to_registry_runner(self):
        market_data = {"trend": "Bullish", "rsi": 40}
        expected = {
            "votes": [],
            "buy_votes": 0,
            "sell_votes": 0,
            "hold_votes": 0,
            "final_vote": "HOLD",
            "vote_strength": 0,
            "total_votes": 0,
        }

        with patch.object(
            strategy_voting_engine,
            "run_registry_strategy_vote",
            return_value=expected,
        ) as registry_vote:
            result = strategy_voting_engine.run_strategy_vote(market_data)

        registry_vote.assert_called_once_with(market_data)
        self.assertIs(result, expected)

    def test_wrapper_preserves_registry_response_without_modification(self):
        expected = {
            "votes": [
                {
                    "strategy": "RSI Pullback",
                    "signal": "BUY",
                    "reason": "reason",
                }
            ],
            "buy_votes": 1,
            "sell_votes": 0,
            "hold_votes": 0,
            "final_vote": "HOLD",
            "vote_strength": 0,
            "total_votes": 1,
            "future_extension": "preserved",
        }

        with patch.object(
            strategy_voting_engine,
            "run_registry_strategy_vote",
            return_value=expected,
        ):
            result = strategy_voting_engine.run_strategy_vote({})

        self.assertEqual(result, expected)

    def test_module_no_longer_imports_legacy_strategy_functions(self):
        path = Path(strategy_voting_engine.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))

        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }

        self.assertNotIn("execute_rsi_pullback", imported_names)
        self.assertNotIn("execute_ma_alignment", imported_names)
        self.assertNotIn("execute_breakout", imported_names)
        self.assertNotIn("execute_trend_following", imported_names)
        self.assertIn("run_registry_strategy_vote", imported_names)

    def test_public_function_name_remains_available(self):
        self.assertTrue(callable(strategy_voting_engine.run_strategy_vote))


if __name__ == "__main__":
    unittest.main()
