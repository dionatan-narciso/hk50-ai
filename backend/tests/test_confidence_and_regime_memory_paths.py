import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app import confidence_calibration_memory
from app import regime_analytics
from app import regime_performance_memory
from app.runtime_paths import resolve_runtime_paths


class ConfidenceAndRegimeMemoryPathTests(unittest.TestCase):
    def test_confidence_memory_uses_configured_paper_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            with patch.object(confidence_calibration_memory, "RUNTIME_PATHS", paths):
                confidence_calibration_memory.update_confidence_calibration(72, 1.0)

            self.assertTrue(paths.paper_confidence_calibration_memory.exists())
            self.assertFalse((Path(tmp) / "confidence_calibration.csv").exists())
            self.assertFalse(paths.replay_dir.exists())
            self.assertFalse(paths.live_dir.exists())

    def test_confidence_legacy_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            legacy = Path(tmp) / "confidence_calibration.csv"
            pd.DataFrame([
                {
                    "confidence_bucket": "65_74",
                    "trades": 10,
                    "wins": 10,
                    "losses": 0,
                    "win_rate": 100,
                    "average_return": 2.0,
                }
            ]).to_csv(legacy, index=False)

            with patch.object(confidence_calibration_memory, "RUNTIME_PATHS", paths):
                result = confidence_calibration_memory.get_confidence_calibration_bonus(72)

            self.assertEqual(result["confidence_calibration_bonus"], 0)
            self.assertEqual(result["reason"], "No confidence calibration data yet.")

    def test_confidence_updates_preserve_running_calculations(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            with patch.object(confidence_calibration_memory, "RUNTIME_PATHS", paths):
                confidence_calibration_memory.update_confidence_calibration(70, 1.0)
                confidence_calibration_memory.update_confidence_calibration(72, -0.5)
                df = pd.read_csv(paths.paper_confidence_calibration_memory)

            row = df.iloc[0]
            self.assertEqual(int(row["trades"]), 2)
            self.assertEqual(int(row["wins"]), 1)
            self.assertEqual(int(row["losses"]), 1)
            self.assertEqual(float(row["win_rate"]), 50.0)
            self.assertEqual(float(row["average_return"]), 0.25)

    def test_confidence_bonus_thresholds_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            paths.paper_dir.mkdir(parents=True)
            rows = [
                {"confidence_bucket": "55_64", "trades": 5, "wins": 4, "losses": 1, "win_rate": 80, "average_return": 0.5},
                {"confidence_bucket": "65_74", "trades": 5, "wins": 2, "losses": 3, "win_rate": 40, "average_return": 0.1},
                {"confidence_bucket": "75_84", "trades": 5, "wins": 3, "losses": 2, "win_rate": 60, "average_return": 0.2},
            ]
            pd.DataFrame(rows).to_csv(paths.paper_confidence_calibration_memory, index=False)

            with patch.object(confidence_calibration_memory, "RUNTIME_PATHS", paths):
                self.assertEqual(confidence_calibration_memory.get_confidence_calibration_bonus(60)["confidence_calibration_bonus"], 5)
                self.assertEqual(confidence_calibration_memory.get_confidence_calibration_bonus(70)["confidence_calibration_bonus"], -7)
                self.assertEqual(confidence_calibration_memory.get_confidence_calibration_bonus(80)["confidence_calibration_bonus"], 0)

    def test_regime_writer_and_reader_share_configured_paper_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            with patch.object(regime_performance_memory, "RUNTIME_PATHS", paths):
                regime_performance_memory.update_regime_memory("RSI", "TRENDING", "NORMAL", 1.0)
                regime_performance_memory.update_regime_memory("RSI", "TRENDING", "NORMAL", -0.5)
                with patch.object(regime_analytics, "load_regime_performance", regime_performance_memory.load_regime_performance):
                    result = regime_analytics.get_regime_bonus("RSI", "TRENDING", "NORMAL")

            self.assertTrue(paths.paper_regime_performance_memory.exists())
            self.assertEqual(result["regime_bonus"], 0)
            self.assertIn("Only 2 regime trade", result["reason"])
            self.assertFalse(paths.replay_dir.exists())
            self.assertFalse(paths.live_dir.exists())

    def test_regime_legacy_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            legacy = Path(tmp) / "regime_performance.csv"
            pd.DataFrame([
                {
                    "strategy": "RSI",
                    "market_regime": "TRENDING",
                    "volatility_regime": "NORMAL",
                    "trades": 10,
                    "wins": 10,
                    "losses": 0,
                    "average_return": 2.0,
                }
            ]).to_csv(legacy, index=False)

            with patch.object(regime_performance_memory, "RUNTIME_PATHS", paths):
                with patch.object(regime_analytics, "load_regime_performance", regime_performance_memory.load_regime_performance):
                    result = regime_analytics.get_regime_bonus("RSI", "TRENDING", "NORMAL")

            self.assertEqual(result["regime_bonus"], 0)
            self.assertEqual(result["reason"], "No regime performance data yet.")

    def test_regime_bonus_thresholds_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_runtime_paths(tmp)
            paths.paper_dir.mkdir(parents=True)
            rows = [
                {"strategy": "Strong", "market_regime": "TRENDING", "volatility_regime": "NORMAL", "trades": 10, "wins": 7, "losses": 3, "average_return": 0.6},
                {"strategy": "Positive", "market_regime": "TRENDING", "volatility_regime": "NORMAL", "trades": 5, "wins": 3, "losses": 2, "average_return": 0.2},
                {"strategy": "Weak", "market_regime": "TRENDING", "volatility_regime": "NORMAL", "trades": 5, "wins": 2, "losses": 3, "average_return": 0.1},
                {"strategy": "Neutral", "market_regime": "TRENDING", "volatility_regime": "NORMAL", "trades": 5, "wins": 3, "losses": 2, "average_return": 0.0},
            ]
            pd.DataFrame(rows).to_csv(paths.paper_regime_performance_memory, index=False)

            with patch.object(regime_performance_memory, "RUNTIME_PATHS", paths):
                with patch.object(regime_analytics, "load_regime_performance", regime_performance_memory.load_regime_performance):
                    self.assertEqual(regime_analytics.get_regime_bonus("Strong", "TRENDING", "NORMAL")["regime_bonus"], 8)
                    self.assertEqual(regime_analytics.get_regime_bonus("Positive", "TRENDING", "NORMAL")["regime_bonus"], 5)
                    self.assertEqual(regime_analytics.get_regime_bonus("Weak", "TRENDING", "NORMAL")["regime_bonus"], -8)
                    self.assertEqual(regime_analytics.get_regime_bonus("Neutral", "TRENDING", "NORMAL")["regime_bonus"], 0)


if __name__ == "__main__":
    unittest.main()
