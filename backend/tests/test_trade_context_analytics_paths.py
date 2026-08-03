import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths
from app.trade_context_analytics import get_trade_context_analytics


COLUMNS = [
    "return_percent",
    "rsi_at_entry",
    "distance_ma20",
    "distance_ma50",
    "trend_strength",
    "previous_candle_return",
    "ma_alignment",
    "rsi_slope",
]


class TradeContextAnalyticsPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(
            os.environ,
            {DATA_ROOT_ENV_VAR: str(self.data_root)},
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def _write_replay(self, rows):
        path = resolve_runtime_paths().replay_trade_journal
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)
        return path

    def test_missing_configured_replay_journal_preserves_failure_contract(self):
        result = get_trade_context_analytics()

        self.assertEqual(result, {
            "status": "failed",
            "reason": "Replay trade file not found.",
        })

    def test_legacy_and_paper_journals_are_ignored(self):
        legacy = self.data_root / "replay_trade_journal.csv"
        paper = resolve_runtime_paths().paper_trade_journal

        legacy.parent.mkdir(parents=True, exist_ok=True)
        paper.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([[1, 30, 1, 1, 1, 1, "Bullish", "Rising"]], columns=COLUMNS).to_csv(legacy, index=False)
        pd.DataFrame([[1, 30, 1, 1, 1, 1, "Bullish", "Rising"]], columns=COLUMNS).to_csv(paper, index=False)

        result = get_trade_context_analytics()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "Replay trade file not found.")

    def test_configured_replay_journal_preserves_context_calculations(self):
        self._write_replay([
            [1.0, 20, 2, 4, 6, 0.5, "Bullish", "Rising"],
            [-0.5, 40, -2, -4, 2, -0.5, "Bearish", "Falling"],
            [0.0, 60, 0, 0, 4, 0, "Neutral", "Flat"],
        ])

        result = get_trade_context_analytics()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["total_rows_loaded"], 3)
        self.assertEqual(result["winner_count"], 1)
        self.assertEqual(result["loser_count"], 2)
        self.assertEqual(result["winner_avg_rsi"], 20.0)
        self.assertEqual(result["loser_avg_rsi"], 50.0)
        self.assertEqual(result["winner_ma_alignment"], {"Bullish": 1})
        self.assertEqual(
            result["loser_rsi_slope"],
            {"Falling": 1, "Flat": 1},
        )

    def test_non_numeric_returns_are_dropped_before_counts(self):
        self._write_replay([
            ["invalid", 10, 1, 1, 1, 1, "Bullish", "Rising"],
            [0.25, 30, 2, 2, 2, 2, "Bullish", "Rising"],
        ])

        result = get_trade_context_analytics()

        self.assertEqual(result["total_rows_loaded"], 1)
        self.assertEqual(result["winner_count"], 1)
        self.assertEqual(result["loser_count"], 0)


if __name__ == "__main__":
    unittest.main()
