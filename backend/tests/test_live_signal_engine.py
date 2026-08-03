import unittest
from contextlib import ExitStack
from unittest.mock import patch

from app import live_signal_engine


class LiveSignalEngineTests(unittest.TestCase):
    def _run_signal(
        self,
        *,
        market_confidence=70,
        director_confidence=70,
        raw_signal="BUY",
        vote_signal="BUY",
        vote_strength=4,
        historical_win_rate=None,
        strategy_bonus=0,
        regime_bonus=0,
        calibration_bonus=0,
        quality_bonus=0,
    ):
        market_regime = {
            "market_regime": "TRENDING",
            "volatility_regime": "NORMAL_VOLATILITY",
            "preferred_strategies": ["RSI Pullback"],
            "blocked_strategies": [],
            "confidence_adjustment": 0,
        }
        strategy_result = {
            "signal": raw_signal,
            "strategy_used": "RSI Pullback",
            "strategy_reason": "Characterization fixture.",
            "market_regime": market_regime,
        }
        rotation_result = {
            "selected_strategy": "RSI Pullback",
            "original_strategy": "RSI Pullback",
            "rotation_changed_strategy": False,
            "rotation_reason": "No rotation needed.",
            "rotation_scores": [],
        }
        vote_result = {
            "final_vote": vote_signal,
            "vote_strength": vote_strength,
            "total_votes": 4,
        }
        research_context = {
            "best_strategy": "RSI Pullback",
            "most_robust_strategy": "RSI Pullback",
            "director_confidence": director_confidence,
            "confidence_label": "Moderate",
        }
        market_data = {
            "price": "24,750.5",
            "confidence": market_confidence,
        }

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(live_signal_engine, "run_strategy_vote", return_value=vote_result)
            )
            stack.enter_context(
                patch.object(live_signal_engine, "execute_strategy", return_value=strategy_result)
            )
            stack.enter_context(
                patch.object(live_signal_engine, "rotate_strategy", return_value=rotation_result)
            )
            stack.enter_context(
                patch.object(live_signal_engine, "get_vote_strength_win_rate", return_value=historical_win_rate)
            )
            stack.enter_context(
                patch.object(
                    live_signal_engine,
                    "apply_trade_analytics_confidence",
                    side_effect=lambda strategy_name, vote_strength, confidence: (
                        confidence,
                        "Trade analytics made no confidence change.",
                    ),
                )
            )
            stack.enter_context(
                patch.object(
                    live_signal_engine,
                    "get_strategy_performance_bonus",
                    return_value={
                        "strategy_performance_bonus": strategy_bonus,
                        "reason": "Strategy fixture.",
                    },
                )
            )
            stack.enter_context(
                patch.object(
                    live_signal_engine,
                    "get_regime_bonus",
                    return_value={"regime_bonus": regime_bonus, "reason": "Regime fixture."},
                )
            )
            stack.enter_context(
                patch.object(
                    live_signal_engine,
                    "get_confidence_calibration_bonus",
                    return_value={
                        "confidence_calibration_bonus": calibration_bonus,
                        "reason": "Calibration fixture.",
                    },
                )
            )
            stack.enter_context(
                patch.object(
                    live_signal_engine,
                    "get_quality_analytics_bonus",
                    return_value={"analytics_bonus": quality_bonus, "reason": "Quality fixture."},
                )
            )

            return live_signal_engine.generate_research_driven_signal(
                market_data,
                research_context,
            )

    def test_clean_price_accepts_numeric_and_comma_formatted_values(self):
        self.assertEqual(live_signal_engine.clean_price(24750), 24750.0)
        self.assertEqual(live_signal_engine.clean_price("24,750.5"), 24750.5)

    def test_quality_thresholds_are_preserved(self):
        cases = {
            54: "REJECT",
            55: "WEAK",
            64: "WEAK",
            65: "MODERATE",
            74: "MODERATE",
            75: "STRONG",
            84: "STRONG",
            85: "EXCEPTIONAL",
        }
        for confidence, expected in cases.items():
            with self.subTest(confidence=confidence):
                self.assertEqual(
                    live_signal_engine.get_quality_from_confidence(confidence),
                    expected,
                )

    def test_research_context_falls_back_when_director_raises(self):
        with patch.object(
            live_signal_engine,
            "run_research_director",
            side_effect=RuntimeError("director unavailable"),
        ):
            result = live_signal_engine.get_research_context()

        self.assertFalse(result["director_available"])
        self.assertEqual(result["best_strategy"], "Unknown")
        self.assertEqual(result["director_confidence"], 50)
        self.assertIn("director unavailable", result["error"])

    def test_combined_confidence_below_55_forces_hold(self):
        result = self._run_signal(
            market_confidence=50,
            director_confidence=50,
            raw_signal="BUY",
            vote_signal="BUY",
        )

        self.assertEqual(result["raw_signal"], "BUY")
        self.assertEqual(result["final_signal"], "HOLD")
        self.assertEqual(result["confidence"], 50)
        self.assertEqual(result["quality"], "REJECT")
        self.assertEqual(
            result["voting_assist_reason"],
            "Combined confidence below 55. Forced HOLD.",
        )

    def test_confirming_vote_without_history_adds_five_confidence(self):
        result = self._run_signal(
            market_confidence=70,
            director_confidence=70,
            raw_signal="BUY",
            vote_signal="BUY",
            historical_win_rate=None,
        )

        self.assertEqual(result["final_signal"], "BUY")
        self.assertEqual(result["confidence"], 75)
        self.assertEqual(result["quality"], "STRONG")
        self.assertIn("Default confidence increased by 5", result["voting_assist_reason"])

    def test_strong_opposing_vote_forces_hold(self):
        result = self._run_signal(
            market_confidence=70,
            director_confidence=70,
            raw_signal="BUY",
            vote_signal="SELL",
            vote_strength=3,
        )

        self.assertEqual(result["raw_signal"], "BUY")
        self.assertEqual(result["final_signal"], "HOLD")
        self.assertEqual(
            result["voting_assist_reason"],
            "Voting strongly disagrees with strategy signal. Forced HOLD.",
        )

    def test_confidence_adjustments_are_applied_in_existing_order(self):
        result = self._run_signal(
            market_confidence=70,
            director_confidence=70,
            raw_signal="BUY",
            vote_signal="BUY",
            historical_win_rate=60,
            strategy_bonus=5,
            regime_bonus=-3,
            calibration_bonus=2,
            quality_bonus=4,
        )

        # 70 base + 10 vote + 5 strategy - 3 regime + 2 calibration + 4 quality.
        self.assertEqual(result["confidence"], 88)
        self.assertEqual(result["quality_before_analytics"], "EXCEPTIONAL")
        self.assertEqual(result["quality"], "EXCEPTIONAL")
        self.assertEqual(result["strategy_performance_bonus"], 5)
        self.assertEqual(result["regime_bonus"], -3)
        self.assertEqual(result["quality_analytics_bonus"], 4)

    def test_apply_voting_assist_preserves_legacy_helper_contract(self):
        vote = {"final_vote": "SELL", "vote_strength": 3, "total_votes": 4}
        signal, confidence, reason = live_signal_engine.apply_voting_assist(
            "BUY",
            70,
            vote,
        )

        self.assertEqual(signal, "HOLD")
        self.assertEqual(confidence, 70)
        self.assertEqual(
            reason,
            "Voting strongly disagrees with strategy signal. Forced HOLD.",
        )


if __name__ == "__main__":
    unittest.main()
