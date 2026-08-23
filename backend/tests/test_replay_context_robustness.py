import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.replay_context_robustness import analyze_context_robustness
from app.replay_journal_repository import get_replay_journal_path


class ReplayContextRobustnessTests(unittest.TestCase):
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

    def _write(self, returns, label="STRONG"):
        path = get_replay_journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for index, value in enumerate(returns):
            rows.append({
                "opened_at": f"2026-01-{index + 1:02d}T00:00:00+00:00",
                "return_percent": value,
                "context_trend_strength": label,
            })
        pd.DataFrame(rows).to_csv(path, index=False)

    def test_marks_consistent_positive_expectancy_as_robust(self):
        self._write([1.0, 0.5, 0.8, 0.2, 0.7, 0.3])
        result = analyze_context_robustness(min_trades=6, max_dimensions=1, folds=3)
        row = result["rows"][0]
        self.assertTrue(row["robust"])
        self.assertEqual(row["positive_folds"], 3)
        self.assertEqual(row["fold_consistency_percent"], 100.0)

    def test_rejects_pattern_that_reverses_in_later_fold(self):
        self._write([1.0, 0.5, 0.8, 0.2, -1.5, -1.0])
        result = analyze_context_robustness(min_trades=6, max_dimensions=1, folds=3)
        row = result["rows"][0]
        self.assertFalse(row["robust"])
        self.assertLess(row["fold_consistency_percent"], 100.0)

    def test_marks_consistent_negative_expectancy_as_robust_negative(self):
        self._write([-1.0, -0.5, -0.8, -0.2, -0.7, -0.3], label="WEAK")
        result = analyze_context_robustness(min_trades=6, max_dimensions=1, folds=3)
        self.assertEqual(len(result["robust_negative"]), 1)
        self.assertEqual(result["robust_negative"][0]["context_trend_strength" if False else "context"]["context_trend_strength"], "WEAK")

    def test_requires_at_least_two_folds(self):
        with self.assertRaises(ValueError):
            analyze_context_robustness(folds=1)

    def test_no_data_is_preserved(self):
        result = analyze_context_robustness()
        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["rows"], [])


if __name__ == "__main__":
    unittest.main()
