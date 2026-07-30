import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import replay_learning_controller
import replay_learning_memory
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class ReplayServicePathTests(unittest.TestCase):
    def test_controller_writes_only_to_configured_replay_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paper_sentinel = paths.paper_dir / "sentinel.txt"
                paper_sentinel.parent.mkdir(parents=True, exist_ok=True)
                paper_sentinel.write_text("paper-state", encoding="utf-8")

                result = replay_learning_controller.record_replay_control_result(
                    total_trades=10,
                    blocked_by_learning=2,
                    win_rate=50,
                    average_return=0.2,
                )

                self.assertTrue(paths.replay_learning_control.exists())
                self.assertEqual(result["decision"], "KEEP_WORKING_CONFIGURATION")
                self.assertEqual(paper_sentinel.read_text(encoding="utf-8"), "paper-state")
                self.assertEqual(
                    list(paths.paper_dir.iterdir()),
                    [paper_sentinel],
                )

    def test_controller_reads_previous_strength_from_configured_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paths.replay_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([{"learning_strength": 1.75}]).to_csv(
                    paths.replay_learning_control,
                    index=False,
                )

                self.assertEqual(
                    replay_learning_controller.get_current_learning_strength(),
                    1.75,
                )

    def test_learning_memory_reads_and_writes_configured_replay_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paths.replay_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([
                    {
                        "strategy": "RSI < 30",
                        "market_regime": "TRENDING",
                        "volatility_regime": "NORMAL_VOLATILITY",
                        "rotation_changed": False,
                        "return_percent": 0.5,
                    },
                    {
                        "strategy": "RSI < 30",
                        "market_regime": "TRENDING",
                        "volatility_regime": "NORMAL_VOLATILITY",
                        "rotation_changed": False,
                        "return_percent": -0.2,
                    },
                ]).to_csv(paths.replay_trade_journal, index=False)

                result = replay_learning_memory.build_replay_learning_memory()

                self.assertEqual(result["status"], "completed")
                self.assertEqual(
                    Path(result["memory_file"]),
                    paths.replay_learning_memory,
                )
                self.assertTrue(paths.replay_learning_memory.exists())
                self.assertFalse(paths.paper_dir.exists())


if __name__ == "__main__":
    unittest.main()
