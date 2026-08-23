import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.replay_context_analysis import analyze_replay_context
from app.replay_context_instrumentation import build_replay_context_fields
from app.replay_journal_repository import append_replay_trade
from app.runtime_paths import resolve_runtime_paths


class ReplayContextInstrumentationTests(unittest.TestCase):
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

    def _trade(self, **overrides):
        trade = {
            "strategy": "RSI < 30",
            "signal": "BUY",
            "entry_price": 20000,
            "exit_price": 20200,
            "return_percent": 1.0,
            "opened_at": "2026-06-01T14:00:00+00:00",
            "closed_at": "2026-06-01T16:00:00+00:00",
            "atr_percent_at_entry": 2.2,
            "trend_at_entry": "Bullish",
            "close_at_entry": 20000,
            "ma20_at_entry": 19900,
            "ma50_at_entry": 19800,
        }
        trade.update(overrides)
        return trade

    def test_builds_context_from_entry_time_values_only(self):
        fields = build_replay_context_fields(self._trade())

        self.assertEqual(fields["context_session"], "EUROPE+US")
        self.assertTrue(fields["context_session_overlap"])
        self.assertEqual(fields["context_volatility"], "HIGH_VOLATILITY")
        self.assertEqual(fields["context_directional_structure"], "BULLISH_STACK")
        self.assertEqual(fields["context_price_position"], "ABOVE_BOTH")
        self.assertEqual(fields["context_ma_alignment"], "BULLISH")
        self.assertEqual(fields["context_nearest_anchor"], "MA20")

    def test_naive_or_invalid_timestamp_is_not_guessed(self):
        for opened_at in ("2026-06-01T14:00:00", "not-a-date", None):
            with self.subTest(opened_at=opened_at):
                fields = build_replay_context_fields(
                    self._trade(opened_at=opened_at)
                )
                self.assertEqual(fields["context_session"], "UNKNOWN")
                self.assertFalse(fields["context_session_overlap"])
                self.assertFalse(fields["context_session_quiet"])

    def test_append_preserves_original_trade_values_and_adds_context(self):
        trade = self._trade(notes="sentinel")
        journal_path = append_replay_trade(trade)
        row = pd.read_csv(journal_path).iloc[0]

        self.assertEqual(row["strategy"], trade["strategy"])
        self.assertEqual(row["return_percent"], trade["return_percent"])
        self.assertEqual(row["notes"], "sentinel")
        self.assertEqual(row["context_session"], "EUROPE+US")
        self.assertEqual(row["context_directional_structure"], "BULLISH_STACK")

    def test_append_writes_only_to_replay_namespace(self):
        append_replay_trade(self._trade())
        paths = resolve_runtime_paths()

        self.assertTrue(paths.replay_trade_journal.exists())
        self.assertFalse(paths.paper_trade_journal.exists())

    def test_analysis_summarizes_categories_and_numeric_winner_loser_values(self):
        append_replay_trade(self._trade(return_percent=1.0))
        append_replay_trade(
            self._trade(
                return_percent=-0.5,
                opened_at="2026-06-01T23:00:00+00:00",
                atr_percent_at_entry=0.5,
                close_at_entry=20000,
                ma20_at_entry=20100,
                ma50_at_entry=20200,
                trend_at_entry="Bearish",
            )
        )

        result = analyze_replay_context()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["total_trades"], 2)
        sessions = {
            row["value"]: row
            for row in result["categorical"]["context_session"]
        }
        self.assertEqual(sessions["EUROPE+US"]["win_rate"], 100.0)
        self.assertEqual(sessions["QUIET"]["win_rate"], 0.0)

        numeric = result["numeric"]["context_ma_separation_percent"]
        self.assertEqual(numeric["observations"], 2)
        self.assertIsNotNone(numeric["winner_average"])
        self.assertIsNotNone(numeric["loser_average"])

    def test_analysis_returns_no_data_without_journal(self):
        result = analyze_replay_context()

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["total_trades"], 0)
        self.assertEqual(result["categorical"], {})
        self.assertEqual(result["numeric"], {})


if __name__ == "__main__":
    unittest.main()
