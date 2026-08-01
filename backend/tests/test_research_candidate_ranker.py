import unittest

from app.research.candidate_ranker import (
    get_analytics_bonus,
    get_walk_forward_candidate_score,
    rank_strategy_candidates,
)


class ResearchCandidateRankerTests(unittest.TestCase):
    def test_analytics_bonus_preserves_legacy_thresholds(self):
        rows = [
            {"strategy": "Strong", "trades": 5, "average_return": 0.6},
            {"strategy": "Positive", "trades": 5, "average_return": 0.1},
            {"strategy": "Negative", "trades": 5, "average_return": -0.1},
            {"strategy": "Too Early", "trades": 4, "average_return": 2.0},
        ]

        self.assertEqual(get_analytics_bonus("Strong", rows), 10)
        self.assertEqual(get_analytics_bonus("Positive", rows), 5)
        self.assertEqual(get_analytics_bonus("Negative", rows), -5)
        self.assertEqual(get_analytics_bonus("Too Early", rows), 0)
        self.assertEqual(get_analytics_bonus("Missing", rows), 0)

    def test_walk_forward_candidate_scores_preserve_legacy_values(self):
        self.assertEqual(get_walk_forward_candidate_score("PASS"), 35)
        self.assertEqual(get_walk_forward_candidate_score("UNSTABLE"), 22)
        self.assertEqual(get_walk_forward_candidate_score("FAIL"), 10)
        self.assertEqual(get_walk_forward_candidate_score("WEAK"), 5)
        self.assertEqual(get_walk_forward_candidate_score("UNKNOWN"), 5)

    def test_candidates_are_sorted_by_final_score(self):
        result = rank_strategy_candidates(
            memory_best_strategy={"strategy": "Memory"},
            best_strategy_lab={"strategy": "Lab"},
            best_parameter_lab={"parameter": "Parameter"},
            best_evolution_lab={"strategy": "Evolution"},
            best_walk_forward={"strategy": "Walk", "robustness": "PASS"},
            best_live_strategy={
                "strategy": "Live",
                "total_trades": 5,
                "win_rate": 55,
                "average_return": 0.2,
            },
            live_score=18,
            strategy_analytics=[
                {"strategy": "Evolution", "trades": 5, "average_return": 0.6},
            ],
        )

        self.assertEqual(result["strategy_candidates"][0]["strategy"], "Evolution")
        self.assertEqual(result["strategy_candidates"][0]["final_score"], 42)
        self.assertEqual(result["selected_strategy"]["strategy"], "Evolution")
        self.assertEqual(result["best_strategy"], "Evolution")

    def test_live_override_preserves_legacy_rule_and_score(self):
        result = rank_strategy_candidates(
            memory_best_strategy={"strategy": "Memory"},
            best_strategy_lab=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy={
                "strategy": "Live",
                "total_trades": 10,
                "win_rate": 60,
                "average_return": 0.1,
            },
            live_score=25,
            strategy_analytics=[
                {"strategy": "Live", "trades": 5, "average_return": 0.6},
            ],
        )

        self.assertEqual(result["selected_strategy"]["source"], "Live Performance Override")
        self.assertEqual(result["selected_strategy"]["final_score"], 55)
        self.assertEqual(result["best_strategy"], "Live")

    def test_live_override_does_not_activate_below_threshold(self):
        result = rank_strategy_candidates(
            memory_best_strategy={"strategy": "Memory"},
            best_strategy_lab=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy={
                "strategy": "Live",
                "total_trades": 9,
                "win_rate": 70,
                "average_return": 0.5,
            },
            live_score=25,
            strategy_analytics=[],
        )

        self.assertNotEqual(result["selected_strategy"]["source"], "Live Performance Override")

    def test_empty_candidates_preserve_legacy_fallback(self):
        memory_best_strategy = None
        result = rank_strategy_candidates(
            memory_best_strategy=memory_best_strategy,
            best_strategy_lab=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy=None,
            live_score=0,
            strategy_analytics=[],
        )

        self.assertEqual(result["strategy_candidates"], [])
        self.assertIsNone(result["selected_strategy"])
        self.assertIs(result["best_strategy"], memory_best_strategy)


if __name__ == "__main__":
    unittest.main()
