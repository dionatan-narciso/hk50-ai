import unittest

from app.research.recommendation_builder import build_research_recommendations


class ResearchRecommendationBuilderTests(unittest.TestCase):
    def test_empty_high_confidence_inputs_return_no_recommendations(self):
        self.assertEqual(
            build_research_recommendations(
                selected_strategy=None,
                best_parameter_lab=None,
                best_evolution_lab=None,
                best_walk_forward=None,
                best_live_strategy=None,
                worst_strategy=None,
                confidence_score=60,
            ),
            [],
        )

    def test_selected_strategy_message_preserves_legacy_wording(self):
        result = build_research_recommendations(
            selected_strategy={
                "strategy": "RSI < 30",
                "source": "Research Memory",
                "final_score": 35,
            },
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy=None,
            worst_strategy=None,
            confidence_score=60,
        )

        self.assertEqual(
            result,
            [
                "Research Director selected RSI < 30 from Research Memory "
                "with final score 35."
            ],
        )

    def test_live_override_message_follows_selected_strategy_message(self):
        result = build_research_recommendations(
            selected_strategy={
                "strategy": "Breakout",
                "source": "Live Performance Override",
                "final_score": 45,
            },
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy=None,
            worst_strategy=None,
            confidence_score=60,
        )

        self.assertEqual(
            result,
            [
                "Research Director selected Breakout from Live Performance "
                "Override with final score 45.",
                "Live performance has enough evidence to override research memory.",
            ],
        )

    def test_optional_research_messages_preserve_order_and_wording(self):
        result = build_research_recommendations(
            selected_strategy=None,
            best_parameter_lab={"parameter": "RSI < 30", "total_return": 2.5},
            best_evolution_lab={"strategy": "Breakout", "total_return": 3.1},
            best_walk_forward={"strategy": "Trend Following", "robustness": "PASS"},
            best_live_strategy={
                "strategy": "RSI < 30",
                "win_rate": 62.5,
                "average_return": 0.4,
            },
            worst_strategy={"strategy": "MACD Only"},
            confidence_score=60,
        )

        self.assertEqual(
            result,
            [
                "Best parameter result is RSI < 30 with 2.5% return.",
                "Best evolved strategy is Breakout with 3.1% return.",
                "Most robust walk forward result is Trend Following with status PASS.",
                "Live paper memory favours RSI < 30 with 62.5% win rate and "
                "0.4% average return.",
                "Avoid or redesign MACD Only because it has the weakest saved result.",
            ],
        )

    def test_low_confidence_warning_appears_below_60(self):
        warning = (
            "Research confidence is not strong enough yet. Focus on robustness "
            "and live paper performance before trusting live signals."
        )

        result = build_research_recommendations(
            selected_strategy=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy=None,
            worst_strategy=None,
            confidence_score=59,
        )

        self.assertEqual(result, [warning])

    def test_low_confidence_warning_is_absent_at_60(self):
        result = build_research_recommendations(
            selected_strategy=None,
            best_parameter_lab=None,
            best_evolution_lab=None,
            best_walk_forward=None,
            best_live_strategy=None,
            worst_strategy=None,
            confidence_score=60,
        )

        self.assertNotIn(
            "Research confidence is not strong enough yet.",
            " ".join(result),
        )


if __name__ == "__main__":
    unittest.main()
