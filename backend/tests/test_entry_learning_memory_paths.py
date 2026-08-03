import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.entry_learning_memory import (
    DEFAULT_ENTRY_WEIGHTS,
    get_paper_entry_memory_path,
    load_entry_weights,
    save_entry_weights,
    update_entry_weights_after_replay,
)
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class EntryLearningMemoryPathTests(unittest.TestCase):
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

    def test_default_path_resolves_inside_paper_directory(self):
        paths = resolve_runtime_paths()

        self.assertEqual(
            get_paper_entry_memory_path(),
            paths.paper_entry_learning_memory,
        )
        self.assertEqual(get_paper_entry_memory_path().parent, paths.paper_dir)

    def test_default_load_and_save_use_only_paper_memory(self):
        weights = DEFAULT_ENTRY_WEIGHTS.copy()
        weights["rsi_rising_bonus"] = 7

        save_entry_weights(weights)
        loaded = load_entry_weights()

        self.assertEqual(loaded["rsi_rising_bonus"], 7)

        paths = resolve_runtime_paths()
        self.assertTrue(paths.paper_entry_learning_memory.exists())
        self.assertFalse(paths.replay_entry_learning_memory.exists())
        self.assertFalse((paths.live_dir / "entry_learning_memory.csv").exists())

    def test_legacy_unscoped_memory_is_ignored(self):
        legacy_path = self.data_root / "entry_learning_memory.csv"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_weights = DEFAULT_ENTRY_WEIGHTS.copy()
        legacy_weights["rsi_rising_bonus"] = 99
        pd.DataFrame([legacy_weights]).to_csv(legacy_path, index=False)

        loaded = load_entry_weights()

        self.assertEqual(
            loaded["rsi_rising_bonus"],
            DEFAULT_ENTRY_WEIGHTS["rsi_rising_bonus"],
        )
        self.assertTrue(resolve_runtime_paths().paper_entry_learning_memory.exists())

    def test_replay_update_writes_only_replay_memory(self):
        result = update_entry_weights_after_replay(
            win_rate=47,
            average_return=0.14,
        )

        paths = resolve_runtime_paths()
        self.assertEqual(
            Path(result["memory_file"]),
            paths.replay_entry_learning_memory,
        )
        self.assertEqual(result["decision"], "STRENGTHEN")
        self.assertTrue(paths.replay_entry_learning_memory.exists())
        self.assertFalse(paths.paper_entry_learning_memory.exists())


if __name__ == "__main__":
    unittest.main()
