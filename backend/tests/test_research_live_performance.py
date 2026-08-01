import unittest

from app.research.live_performance import (
    calculate_live_score,
    rank_live_performance,
)


class ResearchLivePerformanceTests(unittest.TestCase):
    def test_empty_records_preserve_legacy_defaults(self):
        result = rank_live_performance([])

        self.assertEqual(result["live_performance"], [])
        self.assertIsNone(result["best_live_strategy"])
        self.assertEqual(result["live_score"], 0)

    def test_ranking_matches_legacy_sort_order(self):
        records = [
            {
                "strategy": "More Trades",
                "win_rate": 60,
                "average_return": 0.4,
                "total_trades": 20,
            },
            {
                "strategy": "Higher Return",
                "win_rate": 60,
                "average_return": 0.6,
                "total_trades": 5,
            },
            {
                "strategy": "Higher Win Rate",
                "win_rate": 65,
                "average_return": 0.1,
                "total_trades": 3,
            },
        ]

        result = rank_live_performance(records)

        self.assertEqual(
            result["best_live_strategy"]["strategy"],
            "Higher Win Rate",
        )
        self.assertEqual(result["live_performance"], records)

    def test_score_25_threshold_is_unchanged(self):
        self.assertEqual(
            calculate_live_score({
                "total_trades": 10,
                "win_rate": 60,
                "average_return": 0.01,
            }),
            25,
        )

    def test_score_18_threshold_is_unchanged(self):
        self.assertEqual(
            calculate_live_score({
                "total_trades": 5,
                "win_rate": 55,
                "average_return": 0.01,
            }),
            18,
        )

    def test_score_12_threshold_is_unchanged(self):
        self.assertEqual(
            calculate_live_score({
                "total_trades": 3,
                "win_rate": 10,
                "average_return": 0.01,
            }),
            12,
        )

    def test_score_5_threshold_is_unchanged(self):
        self.assertEqual(
            calculate_live_score({
                "total_trades": 1,
                "win_rate": 0,
                "average_return": 0.01,
            }),
            5,
        )

    def test_non_positive_return_receives_no_score(self):
        self.assertEqual(
            calculate_live_score({
                "total_trades": 100,
                "win_rate": 100,
                "average_return": 0,
            }),
            0,
        )


if __name__ == "__main__":
    unittest.main()
