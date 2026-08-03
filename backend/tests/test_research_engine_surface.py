import ast
import unittest
from pathlib import Path


RESEARCH_ENGINE_PATH = Path(__file__).resolve().parents[1] / "app" / "research_engine.py"


class ResearchEngineSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RESEARCH_ENGINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.functions = {
            node.name
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_active_research_functions_remain_available(self):
        expected = {
            "load_hk50_data",
            "backtest_strategy",
            "run_strategy_lab",
            "backtest_rsi_parameter",
            "run_parameter_lab",
            "backtest_evolution_strategy",
            "run_evolution_lab",
            "save_research_results",
            "run_research_memory",
            "walk_forward_test_strategy",
            "run_walk_forward_lab",
        }
        self.assertTrue(expected.issubset(self.functions))

    def test_migrated_responsibilities_are_not_defined(self):
        removed = {
            "run_research_director",
            "save_trade_journal_entry",
            "run_trade_journal",
            "run_live_learning_feed",
        }
        self.assertTrue(removed.isdisjoint(self.functions))

    def test_no_hardcoded_mutable_state_paths_remain(self):
        forbidden = {
            "data/research_results.csv",
            "data/live_strategy_performance.csv",
            "data/trade_journal.csv",
        }
        literals = {
            node.value
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertTrue(forbidden.isdisjoint(literals))

    def test_unused_legacy_dependencies_are_removed(self):
        imported_modules = set()
        imported_names = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
                imported_names.update(alias.name for alias in node.names)

        self.assertNotIn("os", imported_modules)
        self.assertNotIn("app.trade_analytics", imported_modules)
        self.assertNotIn("run_trade_analytics", imported_names)


if __name__ == "__main__":
    unittest.main()
