import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.paper_trade_journal_repository import (
    load_paper_trade_journal,
    run_live_learning_feed,
    run_trade_journal,
    save_trade_journal_entry,
)


class PaperTradeJournalServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {"HK50_DATA_DIR": str(self.data_root)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_manual_save_uses_canonical_journal_and_legacy_contract(self):
        saved = save_trade_journal_entry(
            strategy="RSI < 30",
            direction="BUY",
            entry_price=100,
            exit_price=101,
            notes="Manual test",
        )

        self.assertEqual(saved["result_pct"], 1.0)
        self.assertEqual(saved["return_percent"], 1.0)
        self.assertEqual(saved["strategy"], "RSI < 30")
        self.assertEqual(saved["direction"], "BUY")

        journal = load_paper_trade_journal()
        self.assertEqual(len(journal), 1)
        self.assertEqual(float(journal.iloc[0]["result_pct"]), 1.0)
        self.assertTrue((self.data_root / "paper" / "trade_journal.csv").exists())
        self.assertFalse((self.data_root / "trade_journal.csv").exists())

    def test_summary_preserves_existing_response_shape_and_calculations(self):
        save_trade_journal_entry("A", "BUY", 100, 102)
        save_trade_journal_entry("B", "BUY", 100, 99)

        summary = run_trade_journal()

        self.assertEqual(summary["total_trades"], 2)
        self.assertEqual(summary["win_rate"], 50.0)
        self.assertEqual(summary["average_return"], 0.5)
        self.assertEqual(summary["best_trade"], 2.0)
        self.assertEqual(summary["worst_trade"], -1.0)
        self.assertEqual(len(summary["trades"]), 2)

    def test_empty_summary_preserves_existing_response_shape(self):
        self.assertEqual(
            run_trade_journal(),
            {
                "total_trades": 0,
                "win_rate": 0,
                "average_return": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "trades": [],
            },
        )

    def test_learning_feed_reads_canonical_journal(self):
        save_trade_journal_entry("RSI < 30", "BUY", 100, 101)

        def research_director():
            return {
                "confidence_score": 70,
                "best_strategy": {
                    "strategy": "RSI < 30",
                    "return": 3.2,
                },
                "most_robust": {
                    "strategy": "Trend Following",
                    "robustness": "PASS",
                    "test_return": 1.4,
                    "robustness_score": 90,
                },
            }

        feed = run_live_learning_feed(research_director)["feed"]

        self.assertEqual(feed[0]["source"], "Research")
        self.assertEqual(feed[1]["source"], "Walk Forward")
        self.assertEqual(feed[2]["source"], "Paper Trade")
        self.assertEqual(feed[2]["strategy"], "RSI < 30")
        self.assertEqual(feed[2]["result"], "1.0%")


if __name__ == "__main__":
    unittest.main()
