import unittest

from app.research.confidence_scorer import confidence_label, score_research_confidence


class ResearchConfidenceScorerTests(unittest.TestCase):
    def test_research_return_thresholds_are_unchanged(self):
        cases = [(-1, 0), (0, 0), (0.1, 5), (1, 5), (1.1, 10), (3, 10), (3.1, 15)]

        for total_return, expected in cases:
            result = score_research_confidence(
                best_strategy_lab={"total_return": total_return},
                best_parameter_lab=None,
                best_evolution_lab=None,
                best_walk_forward=None,
                total_tests_saved=0,
                live_score=0,
            )
            self.assertEqual(expected, result["confidence_score"])

    def test_walk_forward_scores_are_unchanged(self):
        expected_scores = {
            "PASS": 25,
            "UNSTABLE": 12,
            "FAIL": 6,
            "WEAK": 2,
        }

        for robustness, expected in expected_scores.items():
            result = score_research_confidence(
                best_strategy_lab=None,
                best_parameter_lab=None,
                best_evolution_lab=None,
                best_walk_forward={"robustness": robustness},
                total_tests_saved=0,
                live_score=0,
            )
            self.assertEqual(expected, result["confidence_score"])

    def test_research_memory_scores_are_unchanged(self):
        cases = [(0, 0), (19, 0), (20, 3), (50, 5), (100, 7), (200, 10)]

        for total_tests, expected in cases:
            result = score_research_confidence(
                best_strategy_lab=None,
                best_parameter_lab=None,
                best_evolution_lab=None,
                best_walk_forward=None,
                total_tests_saved=total_tests,
                live_score=0,
            )
            self.assertEqual(expected, result["confidence_score"])

    def test_live_score_is_added_unchanged(self):
        result = score_research_confidence(
            best_strategy_lab=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            total_tests_saved=0,
            live_score=25,
        )
        self.assertEqual(25, result["confidence_score"])

    def test_score_is_capped_at_100(self):
        result = score_research_confidence(
            best_strategy_lab={"total_return": 4},
            best_parameter_lab={"total_return": 4},
            best_evolution_lab={"total_return": 4},
            best_walk_forward={"robustness": "PASS"},
            total_tests_saved=200,
            live_score=25,
        )
        self.assertEqual(100, result["confidence_score"])

    def test_confidence_label_boundaries_are_unchanged(self):
        cases = [
            (0, "Very Weak"),
            (39, "Very Weak"),
            (40, "Weak"),
            (59, "Weak"),
            (60, "Moderate"),
            (79, "Moderate"),
            (80, "Strong"),
            (100, "Strong"),
        ]

        for score, expected in cases:
            self.assertEqual(expected, confidence_label(score))


if __name__ == "__main__":
    unittest.main()
