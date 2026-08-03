import unittest

from app.position_sizing_engine import calculate_position_size


class PositionSizingEngineTests(unittest.TestCase):
    def test_confidence_bands_preserve_quality_and_base_risk(self):
        cases = [
            (54, "REJECT", 0.0),
            (55, "WEAK", 0.11),
            (64, "WEAK", 0.11),
            (65, "MODERATE", 0.26),
            (74, "MODERATE", 0.26),
            (75, "STRONG", 0.49),
            (84, "STRONG", 0.49),
            (85, "EXCEPTIONAL", 0.75),
        ]

        for confidence, quality, expected_risk in cases:
            with self.subTest(confidence=confidence):
                result = calculate_position_size(
                    confidence,
                    risk="Medium",
                    live_score=0,
                    robustness="UNKNOWN",
                )
                self.assertEqual(result["quality"], quality)
                self.assertEqual(result["risk_per_trade_percent"], expected_risk)

    def test_high_and_low_market_risk_multipliers_are_preserved(self):
        high = calculate_position_size(75, "High", live_score=10)
        low = calculate_position_size(75, "Low", live_score=10)
        medium = calculate_position_size(75, "Medium", live_score=10)

        self.assertEqual(high["risk_per_trade_percent"], 0.33)
        self.assertEqual(medium["risk_per_trade_percent"], 0.65)
        self.assertEqual(low["risk_per_trade_percent"], 0.78)

    def test_unstable_robustness_halves_risk_after_market_adjustment(self):
        result = calculate_position_size(
            75,
            risk="Low",
            live_score=10,
            robustness="UNSTABLE",
        )

        self.assertEqual(result["quality"], "STRONG")
        self.assertEqual(result["risk_per_trade_percent"], 0.39)
        self.assertEqual(result["robustness_adjusted"], "UNSTABLE")

    def test_fail_robustness_forces_reject_and_no_trade(self):
        result = calculate_position_size(
            95,
            risk="Low",
            live_score=20,
            robustness="FAIL",
        )

        self.assertEqual(result["quality"], "REJECT")
        self.assertEqual(result["risk_per_trade_percent"], 0)
        self.assertEqual(result["position_size_label"], "NO TRADE")
        self.assertEqual(result["suggested_exposure_percent"], 0)

    def test_live_score_adjustments_are_applied_after_robustness(self):
        positive = calculate_position_size(
            75,
            risk="Medium",
            live_score=15,
            robustness="UNSTABLE",
        )
        neutral = calculate_position_size(
            75,
            risk="Medium",
            live_score=10,
            robustness="UNSTABLE",
        )
        non_positive = calculate_position_size(
            75,
            risk="Medium",
            live_score=0,
            robustness="UNSTABLE",
        )

        self.assertEqual(positive["risk_per_trade_percent"], 0.39)
        self.assertEqual(neutral["risk_per_trade_percent"], 0.33)
        self.assertEqual(non_positive["risk_per_trade_percent"], 0.24)

    def test_position_size_labels_preserve_boundaries(self):
        cases = [
            (54, "Medium", 10, "NO TRADE"),
            (55, "Medium", 10, "VERY SMALL"),
            (65, "Medium", 10, "SMALL"),
            (75, "Medium", 10, "MEDIUM"),
            (85, "Medium", 15, "LARGE"),
        ]

        for confidence, risk, live_score, label in cases:
            with self.subTest(confidence=confidence, label=label):
                result = calculate_position_size(
                    confidence,
                    risk,
                    live_score=live_score,
                )
                self.assertEqual(result["position_size_label"], label)

    def test_risk_is_clamped_to_one_point_five_percent(self):
        result = calculate_position_size(
            100,
            risk="Low",
            live_score=20,
            robustness="UNKNOWN",
        )

        self.assertEqual(result["risk_per_trade_percent"], 1.44)
        self.assertLessEqual(result["risk_per_trade_percent"], 1.5)

    def test_response_contract_and_exposure_multiplier_are_preserved(self):
        result = calculate_position_size(
            75,
            risk="High",
            live_score=10,
            robustness="UNKNOWN",
        )

        self.assertEqual(
            set(result),
            {
                "quality",
                "position_size_label",
                "risk_per_trade_percent",
                "suggested_exposure_percent",
                "risk_adjusted",
                "robustness_adjusted",
                "live_score_used",
            },
        )
        self.assertEqual(result["suggested_exposure_percent"], 1.32)
        self.assertEqual(result["risk_adjusted"], "High")
        self.assertEqual(result["live_score_used"], 10)


if __name__ == "__main__":
    unittest.main()
