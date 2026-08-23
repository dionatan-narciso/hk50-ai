import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.replay_context_matrix import analyze_context_matrix
from app.replay_journal_repository import get_replay_journal_path


class ReplayContextMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(
            os.environ,
            {"HK50_DATA_DIR": str(self.root / "runtime-data")},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def _write_rows(self, rows):
        path = get_replay_journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(path, index=False)

    def test_excludes_combinations_below_minimum_sample(self):
        self._write_rows([
            {"return_percent": 1.0, "context_trend_strength": "STRONG"},
            {"return_percent": 0.5, "context_trend_strength": "STRONG"},
            {"return_percent": -1.0, "context_trend_strength": "WEAK"},
        ])

        result = analyze_context_matrix(min_trades=2, max_dimensions=1)
        contexts = [row["context"] for row in result["rows"]]

        self.assertIn({"context_trend_strength": "STRONG"}, contexts)
        self.assertNotIn({"context_trend_strength": "WEAK"}, contexts)

    def test_ranks_by_expectancy_not_win_rate(self):
        self._write_rows([
            {"return_percent": 0.1, "context_trend_strength": "FLAT"},
            {"return_percent": 0.1, "context_trend_strength": "FLAT"},
            {"return_percent": -1.0, "context_trend_strength": "FLAT"},
            {"return_percent": 0.8, "context_trend_strength": "STRONG"},
            {"return_percent": -0.2, "context_trend_strength": "STRONG"},
            {"return_percent": 0.8, "context_trend_strength": "STRONG"},
        ])

        result = analyze_context_matrix(min_trades=3, max_dimensions=1)

        self.assertEqual(result["rows"][0]["context"]["context_trend_strength"], "STRONG")
        self.assertGreater(result["rows"][0]["average_return"], 0)
        flat = next(row for row in result["rows"] if row["context"]["context_trend_strength"] == "FLAT")
        self.assertGreater(flat["win_rate"], 50)
        self.assertLess(flat["average_return"], 0)

    def test_builds_two_dimension_combinations(self):
        rows = []
        for value in (1.0, 0.5, -0.2, 0.7):
            rows.append({
                "return_percent": value,
                "context_trend_strength": "STRONG",
                "context_htf_agreement": "NEUTRAL",
            })
        self._write_rows(rows)

        result = analyze_context_matrix(min_trades=4, max_dimensions=2)
        pair = next(
            row for row in result["rows"]
            if row["dimensions"] == ["context_trend_strength", "context_htf_agreement"]
        )

        self.assertEqual(pair["trades"], 4)
        self.assertEqual(pair["context"]["context_trend_strength"], "STRONG")
        self.assertEqual(pair["context"]["context_htf_agreement"], "NEUTRAL")

    def test_reports_profit_factor_and_total_return(self):
        self._write_rows([
            {"return_percent": 1.0, "context_session": "ASIA"},
            {"return_percent": 0.5, "context_session": "ASIA"},
            {"return_percent": -0.5, "context_session": "ASIA"},
        ])

        result = analyze_context_matrix(min_trades=3, max_dimensions=1)
        row = result["rows"][0]

        self.assertEqual(row["total_return"], 1.0)
        self.assertEqual(row["profit_factor"], 3.0)
        self.assertEqual(row["average_return"], 0.333)

    def test_invalid_controls_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze_context_matrix(min_trades=0)
        with self.assertRaises(ValueError):
            analyze_context_matrix(max_dimensions=0)

    def test_no_journal_returns_no_data(self):
        result = analyze_context_matrix()
        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["rows"], [])


if __name__ == "__main__":
    unittest.main()
