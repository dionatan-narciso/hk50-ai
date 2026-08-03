from unittest.mock import Mock, patch
import unittest

import pandas as pd

from app.research.source_loader import load_research_sources


class ResearchSourceLoaderTests(unittest.TestCase):
    @patch("app.research.source_loader.run_trade_analytics")
    @patch("app.research.source_loader.run_research_memory")
    @patch("app.research.source_loader.run_walk_forward_lab")
    @patch("app.research.source_loader.run_evolution_lab")
    @patch("app.research.source_loader.run_parameter_lab")
    @patch("app.research.source_loader.run_strategy_lab")
    @patch("app.research.source_loader.load_live_strategy_performance")
    def test_loader_preserves_existing_source_contract(
        self,
        load_live,
        run_strategy,
        run_parameter,
        run_evolution,
        run_walk_forward,
        run_memory,
        run_analytics,
    ):
        load_live.return_value = pd.DataFrame([
            {"strategy": "Live", "win_rate": 60, "average_return": 1.0, "total_trades": 10}
        ])
        run_strategy.return_value = {"strategies": [{"strategy": "A"}]}
        run_parameter.return_value = {"parameter_tests": [{"parameter": "B"}]}
        run_evolution.return_value = {"evolution_tests": [{"strategy": "C"}]}
        run_walk_forward.return_value = {"walk_forward_tests": [{"strategy": "D"}]}
        run_memory.return_value = {"best_strategy": "A"}
        run_analytics.return_value = {"strategy_performance": []}

        result = load_research_sources()

        self.assertEqual(result["strategy_lab"], [{"strategy": "A"}])
        self.assertEqual(result["parameter_lab"], [{"parameter": "B"}])
        self.assertEqual(result["evolution_lab"], [{"strategy": "C"}])
        self.assertEqual(result["walk_forward"], [{"strategy": "D"}])
        self.assertEqual(result["memory"], {"best_strategy": "A"})
        self.assertEqual(result["analytics"], {"strategy_performance": []})
        self.assertEqual(result["live_records"][0]["strategy"], "Live")

    @patch("app.research.source_loader.run_trade_analytics", return_value={})
    @patch("app.research.source_loader.run_research_memory", return_value={})
    @patch("app.research.source_loader.run_walk_forward_lab", return_value={})
    @patch("app.research.source_loader.run_evolution_lab", return_value={})
    @patch("app.research.source_loader.run_parameter_lab", return_value={})
    @patch("app.research.source_loader.run_strategy_lab", return_value={})
    @patch("app.research.source_loader.load_live_strategy_performance", return_value=pd.DataFrame())
    def test_missing_collection_keys_preserve_empty_defaults(self, *mocks):
        result = load_research_sources()

        self.assertEqual(result["strategy_lab"], [])
        self.assertEqual(result["parameter_lab"], [])
        self.assertEqual(result["evolution_lab"], [])
        self.assertEqual(result["walk_forward"], [])
        self.assertEqual(result["live_records"], [])

    @patch("app.research.director.build_research_director_result")
    @patch("app.research.director.load_research_sources")
    def test_director_passes_loader_result_directly_to_builder(self, load_sources, build_result):
        source_payload = {
            "strategy_lab": [],
            "parameter_lab": [],
            "evolution_lab": [],
            "walk_forward": [],
            "memory": {},
            "analytics": {},
            "live_records": [],
        }
        load_sources.return_value = source_payload
        build_result.return_value = {"best_strategy": None}

        from app.research.director import run_research_director

        result = run_research_director()

        build_result.assert_called_once_with(**source_payload)
        self.assertEqual(result, {"best_strategy": None})

    def test_loader_result_contains_only_director_input_keys(self):
        expected_keys = {
            "strategy_lab",
            "parameter_lab",
            "evolution_lab",
            "walk_forward",
            "memory",
            "analytics",
            "live_records",
        }

        with (
            patch("app.research.source_loader.load_live_strategy_performance", return_value=pd.DataFrame()),
            patch("app.research.source_loader.run_strategy_lab", return_value={}),
            patch("app.research.source_loader.run_parameter_lab", return_value={}),
            patch("app.research.source_loader.run_evolution_lab", return_value={}),
            patch("app.research.source_loader.run_walk_forward_lab", return_value={}),
            patch("app.research.source_loader.run_research_memory", return_value={}),
            patch("app.research.source_loader.run_trade_analytics", return_value={}),
        ):
            self.assertEqual(set(load_research_sources()), expected_keys)


if __name__ == "__main__":
    unittest.main()
