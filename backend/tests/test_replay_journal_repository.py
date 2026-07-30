import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.replay_journal_repository import (
    append_replay_trade,
    get_replay_journal_path,
    reset_replay_journal,
)
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class ReplayJournalRepositoryTests(unittest.TestCase):
    def test_journal_path_uses_configured_replay_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {DATA_ROOT_ENV_VAR: temp_dir},
                clear=True,
            ):
                paths = resolve_runtime_paths()
                journal_path = get_replay_journal_path()

            self.assertEqual(journal_path, paths.replay_trade_journal)
            self.assertEqual(journal_path.parent, paths.replay_dir)
            self.assertNotEqual(journal_path.parent, paths.paper_dir)

    def test_append_writes_only_to_replay_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {DATA_ROOT_ENV_VAR: temp_dir},
                clear=True,
            ):
                paths = resolve_runtime_paths()
                paper_files = (
                    paths.paper_trade_journal,
                    paths.paper_open_position,
                    paths.paper_last_signal,
                    paths.paper_entry_learning_memory,
                )

                for paper_file in paper_files:
                    paper_file.parent.mkdir(parents=True, exist_ok=True)
                    paper_file.write_text("paper-sentinel", encoding="utf-8")

                first_trade = {
                    "strategy": "RSI < 30",
                    "signal": "BUY",
                    "return_percent": 0.5,
                }
                second_trade = {
                    "strategy": "Trend Following",
                    "signal": "SELL",
                    "return_percent": -0.25,
                }

                append_replay_trade(first_trade)
                append_replay_trade(second_trade)

                journal = pd.read_csv(paths.replay_trade_journal)

                self.assertEqual(len(journal), 2)
                self.assertEqual(journal.iloc[0]["strategy"], "RSI < 30")
                self.assertEqual(journal.iloc[1]["strategy"], "Trend Following")

                for paper_file in paper_files:
                    self.assertEqual(
                        paper_file.read_text(encoding="utf-8"),
                        "paper-sentinel",
                    )

    def test_reset_removes_only_replay_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {DATA_ROOT_ENV_VAR: temp_dir},
                clear=True,
            ):
                paths = resolve_runtime_paths()
                paths.replay_trade_journal.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                paths.replay_trade_journal.write_text(
                    "replay-data",
                    encoding="utf-8",
                )
                paths.paper_trade_journal.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                paths.paper_trade_journal.write_text(
                    "paper-sentinel",
                    encoding="utf-8",
                )

                returned_path = reset_replay_journal()

                self.assertEqual(returned_path, paths.replay_trade_journal)
                self.assertFalse(paths.replay_trade_journal.exists())
                self.assertEqual(
                    paths.paper_trade_journal.read_text(encoding="utf-8"),
                    "paper-sentinel",
                )


if __name__ == "__main__":
    unittest.main()
