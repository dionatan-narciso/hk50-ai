import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import replay_exit_analysis
import replay_exit_reason_analysis
import replay_penalty_engine
import replay_winner_loser_analysis
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class SpecializedReplayReaderPathTests(unittest.TestCase):
    def _write_replay_journal(self, paths):
        paths.replay_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([
            {
                "return_percent": 1.0,
                "result": "REPLAY_TRAILING_EXIT",
                "confidence": 60,
                "rsi_at_entry": 25,
                "atr_percent_at_entry": 0.4,
                "quality_score": 70,
                "trend_at_entry": "Bullish",
                "risk_at_entry": "Low",
            },
            {
                "return_percent": -0.5,
                "result": "REPLAY_ADAPTIVE_STOP_LOSS",
                "confidence": 50,
                "rsi_at_entry": 30,
                "atr_percent_at_entry": 0.8,
                "quality_score": 50,
                "trend_at_entry": "Neutral",
                "risk_at_entry": "Medium",
            },
        ]).to_csv(paths.replay_trade_journal, index=False)

    def test_specialised_analyses_read_configured_replay_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                self._write_replay_journal(paths)

                exit_result = replay_exit_analysis.analyze_replay_exits()
                reason_result = replay_exit_reason_analysis.analyze_replay_exit_reasons()
                comparison_result = replay_winner_loser_analysis.analyze_winners_vs_losers()

                self.assertEqual(exit_result["status"], "completed")
                self.assertEqual(exit_result["profit_factor"], 2.0)
                self.assertEqual(reason_result["status"], "completed")
                self.assertEqual(reason_result["total_trades"], 2)
                self.assertEqual(comparison_result["winner_count"], 1)
                self.assertEqual(comparison_result["loser_count"], 1)

    def test_specialised_analyses_ignore_paper_journal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paths.paper_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([{"return_percent": 10.0}]).to_csv(
                    paths.paper_trade_journal,
                    index=False,
                )

                self.assertEqual(
                    replay_exit_analysis.analyze_replay_exits()["status"],
                    "no_replay_data",
                )
                self.assertEqual(
                    replay_exit_reason_analysis.analyze_replay_exit_reasons()["status"],
                    "no_replay_data",
                )
                self.assertEqual(
                    replay_winner_loser_analysis.analyze_winners_vs_losers()["status"],
                    "no_replay_data",
                )

    def test_penalty_engine_reads_configured_replay_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()
                paths.replay_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame([
                    {
                        "learning_type": "strategy",
                        "key": "RSI < 30",
                        "score_adjustment": -3,
                        "win_rate": 40,
                        "average_return": -0.1,
                    },
                    {
                        "learning_type": "strategy+market_regime",
                        "key": "RSI < 30 | TRENDING",
                        "score_adjustment": -5,
                        "win_rate": 30,
                        "average_return": -0.2,
                    },
                ]).to_csv(paths.replay_learning_memory, index=False)

                with patch.object(
                    replay_penalty_engine,
                    "get_current_learning_strength",
                    return_value=2.0,
                ):
                    result = replay_penalty_engine.get_replay_penalty(
                        strategy="RSI < 30",
                        market_regime="TRENDING",
                    )

                self.assertTrue(result["penalty_available"])
                self.assertEqual(result["total_adjustment"], -10)
                self.assertEqual(result["learning_strength"], 2.0)


if __name__ == "__main__":
    unittest.main()
