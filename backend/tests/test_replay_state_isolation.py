import csv
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.adaptive_entry_weight_tuner import tune_entry_weights
from app.entry_learning_memory import update_entry_weights_after_replay
from app.runtime_paths import resolve_runtime_paths


class ReplayStateIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.original_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.original_cwd)

        self.env_patch = patch.dict(
            os.environ,
            {"HK50_DATA_DIR": str(self.root / "runtime-data")},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        self.paths = resolve_runtime_paths()
        self.legacy_paper_memory = self.root / "data" / "entry_learning_memory.csv"
        self.legacy_paper_memory.parent.mkdir(parents=True, exist_ok=True)
        self.paper_sentinel = "paper-state-must-not-change\n"
        self.legacy_paper_memory.write_text(self.paper_sentinel, encoding="utf-8")

    def test_standard_replay_learning_writes_only_replay_memory(self):
        result = update_entry_weights_after_replay(
            win_rate=50,
            average_return=0.20,
        )

        self.assertEqual(
            self.legacy_paper_memory.read_text(encoding="utf-8"),
            self.paper_sentinel,
        )
        self.assertTrue(self.paths.replay_entry_learning_memory.exists())
        self.assertEqual(
            Path(result["memory_file"]),
            self.paths.replay_entry_learning_memory,
        )
        self.assertFalse(self.paths.paper_entry_learning_memory.exists())

    def test_adaptive_tuner_writes_only_replay_files(self):
        def deterministic_replay(entry_weights_override):
            return {
                "win_rate": 50,
                "average_return": 0.20,
                "weights": entry_weights_override,
            }

        result = tune_entry_weights(deterministic_replay)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            self.legacy_paper_memory.read_text(encoding="utf-8"),
            self.paper_sentinel,
        )
        self.assertTrue(self.paths.replay_entry_learning_memory.exists())
        self.assertTrue(self.paths.replay_entry_weight_tuning_log.exists())
        self.assertFalse(self.paths.paper_entry_learning_memory.exists())

        with self.paths.replay_entry_weight_tuning_log.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file_handle:
            rows = list(csv.DictReader(file_handle))

        self.assertEqual(len(rows), 12)

    def test_replay_learning_does_not_create_paper_trade_state(self):
        update_entry_weights_after_replay(
            win_rate=40,
            average_return=0.05,
        )

        self.assertFalse(self.paths.paper_trade_journal.exists())
        self.assertFalse(self.paths.paper_open_position.exists())
        self.assertFalse(self.paths.paper_last_signal.exists())


if __name__ == "__main__":
    unittest.main()
