import unittest

from app.research.director import build_research_director_result


class ModularResearchDirectorTests(unittest.TestCase):
    def setUp(self):
        self.strategy_lab = [{"strategy": "Strategy Lab Winner", "total_return": 4.0}]
        self.parameter_lab = [{"parameter": "RSI < 30", "total_return": 2.0}]
        self.evolution_lab = [{"strategy": "Evolved Winner", "total_return": 1.0}]
        self.walk_forward = [{"strategy": "Robust Winner", "robustness": "PASS"}]
        self.memory = {
            "best_strategy": {"strategy": "Memory Winner"},
            "worst_strategy": {"strategy": "Weak Strategy"},
            "total_tests_saved": 50,
        }
        self.analytics = {
            "strategy_performance": [
                {"strategy": "Memory Winner", "trades": 5, "average_return": 0.6},
                {"strategy": "Paper Winner", "trades": 5, "average_return": 0.7},
            ]
        }

    def build(self, live_records=None):
        return build_research_director_result(
            strategy_lab=self.strategy_lab,
            parameter_lab=self.parameter_lab,
            evolution_lab=self.evolution_lab,
            walk_forward=self.walk_forward,
            memory=self.memory,
            analytics=self.analytics,
            live_records=live_records or [],
        )

    def test_candidate_scores_match_legacy_rules(self):
        result = self.build()
        candidates = {row["source"]: row for row in result["strategy_candidates"]}

        self.assertEqual(candidates["Research Memory"]["final_score"], 45)
        self.assertEqual(candidates["Strategy Lab"]["final_score"], 30)
        self.assertEqual(candidates["Parameter Lab"]["final_score"], 28)
        self.assertEqual(candidates["Evolution Lab"]["final_score"], 32)
        self.assertEqual(candidates["Walk Forward Lab"]["final_score"], 35)
        self.assertEqual(result["best_strategy"], "Memory Winner")

    def test_confidence_score_matches_legacy_thresholds(self):
        result = self.build()
        # 15 strategy + 10 parameter + 5 evolution + 25 walk-forward + 5 memory
        self.assertEqual(result["confidence_score"], 60)
        self.assertEqual(result["confidence_label"], "Moderate")

    def test_strong_live_memory_keeps_legacy_override_behavior(self):
        result = self.build([
            {
                "strategy": "Paper Winner",
                "wins": 7,
                "losses": 3,
                "total_trades": 10,
                "win_rate": 70,
                "average_return": 0.8,
            }
        ])

        self.assertEqual(result["live_score"], 25)
        self.assertEqual(result["best_strategy"], "Paper Winner")
        self.assertEqual(result["selected_strategy"]["source"], "Live Performance Override")
        self.assertEqual(result["selected_strategy"]["final_score"], 55)


if __name__ == "__main__":
    unittest.main()
