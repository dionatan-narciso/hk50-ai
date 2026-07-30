import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app import automatic_signal_tracker
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class PaperPositionStatePathTests(unittest.TestCase):
    def test_open_position_round_trip_uses_configured_paper_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                position = {
                    "symbol": "HK50",
                    "entry_price": 25000,
                    "signal": "BUY",
                    "confidence": 70,
                }

                automatic_signal_tracker.save_open_position(position)

                self.assertTrue(paths.paper_open_position.exists())
                self.assertFalse(paths.replay_dir.exists())
                self.assertEqual(
                    automatic_signal_tracker.load_open_position()["signal"],
                    "BUY",
                )

                automatic_signal_tracker.clear_open_position()
                self.assertFalse(paths.paper_open_position.exists())

    def test_last_signal_round_trip_uses_configured_paper_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()

                automatic_signal_tracker.save_last_signal("SELL")

                self.assertTrue(paths.paper_last_signal.exists())
                self.assertEqual(automatic_signal_tracker.load_last_signal(), "SELL")
                self.assertFalse(paths.replay_dir.exists())

    def test_legacy_unscoped_state_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_root = os.path.join(temp_dir, "legacy-working-directory")
            os.makedirs(os.path.join(legacy_root, "data"), exist_ok=True)

            pd.DataFrame([{
                "symbol": "HK50",
                "entry_price": 25000,
                "signal": "BUY",
            }]).to_csv(
                os.path.join(legacy_root, "data", "open_position.csv"),
                index=False,
            )
            pd.DataFrame([{"signal": "BUY"}]).to_csv(
                os.path.join(legacy_root, "data", "last_signal.csv"),
                index=False,
            )

            configured_root = os.path.join(temp_dir, "configured-data")
            with patch.dict(
                os.environ,
                {DATA_ROOT_ENV_VAR: configured_root},
                clear=True,
            ):
                previous_cwd = os.getcwd()
                try:
                    os.chdir(legacy_root)
                    self.assertIsNone(automatic_signal_tracker.load_open_position())
                    self.assertIsNone(automatic_signal_tracker.load_last_signal())
                finally:
                    os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
