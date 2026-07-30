import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import replay_analytics
from app.historical_replay_summary import get_historical_replay_summary
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class ReplayReaderPathTests(unittest.TestCase):
    def test_readers_return_empty_when_configured_replay_journal_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                self.assertEqual(
                    replay_analytics.get_replay_analytics()["status"],
                    "no_replay_data",
                )
                self.assertEqual(
                    get_historical_replay_summary()["status"],
                    "empty",
                )

    def test_readers_use_configured_replay_journal(self):
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
                        "return_percent": -0.1,
                    },
                ]).to_csv(paths.replay_trade_journal, index=False)

                analytics = replay_analytics.get_replay_analytics()
                summary = get_historical_replay_summary()

                self.assertEqual(analytics["status"], "completed")
                self.assertEqual(analytics["total_trades"], 2)
                self.assertEqual(analytics["wins"], 1)
                self.assertEqual(analytics["losses"], 1)
                self.assertEqual(analytics["average_return"], 0.2)

                self.assertEqual(summary["status"], "completed")
                self.assertEqual(summary["total_trades"], 2)
                self.assertEqual(summary["wins"], 1)
                self.assertEqual(summary["losses"], 1)
                self.assertEqual(summary["average_return"], 0.2)

    def test_readers_ignore_paper_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paths.paper_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([
                    {
                        "strategy": "PAPER_ONLY",
                        "return_percent": 99.0,
                    }
                ]).to_csv(paths.paper_trade_journal, index=False)

                self.assertEqual(
                    replay_analytics.get_replay_analytics()["status"],
                    "no_replay_data",
                )
                self.assertEqual(
                    get_historical_replay_summary()["status"],
                    "empty",
                )


if __name__ == "__main__":
    unittest.main()
