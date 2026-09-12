import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.oos_validation.forward_engine import run_forward_batch_replay


class ForwardOosEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _fixture(self):
        index = pd.to_datetime(
            [
                "2026-09-11T10:00:00Z",
                "2026-09-12T12:00:00Z",
                "2026-09-12T13:00:00Z",
            ],
            utc=True,
        )
        data = pd.DataFrame(
            {
                "Open": [100.0, 99.0, 99.0],
                "High": [100.0, 99.0, 99.0],
                "Low": [100.0, 99.0, 99.0],
                "Close": [100.0, 99.0, 99.0],
                "ATR_PERCENT": [1.0, 1.0, 1.0],
            },
            index=index,
        )
        folder = Path(self.temp_dir.name) / "validation" / "forward_batches" / "batch-002"
        folder.mkdir(parents=True, exist_ok=True)
        paths = {
            "folder": folder,
            "dataset": folder / "market_data.csv",
            "manifest": folder / "dataset_manifest.json",
            "journal": folder / "trade_journal.csv",
            "report": folder / "result_report.json",
        }
        manifest = {
            "batch_id": "batch-002",
            "candidate_snapshot_sha256": "a" * 64,
            "dataset_sha256": "b" * 64,
            "execution_start": "2026-09-11T00:00:00+00:00",
            "validation_window": {
                "start": "2026-09-12T11:00:00+00:00",
                "end": "2026-09-13T00:00:00+00:00",
            },
        }
        return manifest, data, paths

    @patch("app.oos_validation.forward_engine.discovery_state_fingerprint", return_value={})
    @patch("app.oos_validation.forward_engine.derive_replay_higher_timeframe_context")
    @patch("app.oos_validation.forward_engine.calculate_trade_context")
    @patch("app.oos_validation.forward_engine.calculate_entry_context_score")
    @patch("app.oos_validation.forward_engine.get_replay_penalty")
    @patch("app.oos_validation.forward_engine.get_adaptive_replay_settings")
    @patch("app.oos_validation.forward_engine.run_ai_replay_decision")
    @patch("app.oos_validation.forward_engine.build_market_snapshot")
    @patch("app.oos_validation.forward_engine._load_replay_entry_weights", return_value={})
    @patch("app.oos_validation.forward_engine._load_batch")
    def test_position_opened_before_batch_can_close_and_score_inside_batch(
        self,
        load_batch,
        entry_weights,
        build_snapshot,
        decision,
        settings,
        penalty,
        entry_score,
        trade_context,
        htf,
        fingerprint,
    ):
        manifest, data, paths = self._fixture()
        load_batch.return_value = (manifest, data, paths)
        build_snapshot.side_effect = lambda row, previous: {
            "price": float(row["Close"]),
            "atr_percent": 1.0,
            "confidence": 60,
        }
        decision.side_effect = [
            {"signal": "BUY", "strategy": "TEST"},
            {"signal": "HOLD", "strategy": "TEST"},
            {"signal": "HOLD", "strategy": "TEST"},
        ]
        settings.return_value = {"activation": 0.75, "pullback": 0.35, "stop_loss": -0.5}
        penalty.return_value = {"total_adjustment": 0, "reasons": []}
        entry_score.return_value = {"entry_context_adjustment": 0, "entry_context_reasons": []}
        trade_context.return_value = {
            "close_at_entry": 100.0,
            "ma20_at_entry": 100.0,
            "ma50_at_entry": 100.0,
            "distance_ma20": 0.0,
            "distance_ma50": 0.0,
            "previous_candle_return": 0.0,
            "trend_strength": "FLAT",
            "ma_alignment": "NEUTRAL",
            "rsi_slope": "UNKNOWN",
        }
        htf.return_value.trend_4h = "Neutral"
        htf.return_value.trend_1d = "Neutral"
        htf.return_value.agreement = "NEUTRAL"
        htf.return_value.aligned_direction = None

        result = run_forward_batch_replay("batch-002")

        self.assertEqual(result["total_trades"], 1)
        self.assertTrue(paths["journal"].exists())
        journal = pd.read_csv(paths["journal"])
        self.assertEqual(len(journal), 1)
        self.assertTrue(str(journal.iloc[0]["opened_at"]).startswith("2026-09-11"))
        self.assertTrue(str(journal.iloc[0]["closed_at"]).startswith("2026-09-12"))

    @patch("app.oos_validation.forward_engine.discovery_state_fingerprint", return_value={})
    @patch("app.oos_validation.forward_engine.calculate_trade_context", return_value={})
    @patch("app.oos_validation.forward_engine.calculate_entry_context_score", return_value={"entry_context_adjustment": 0, "entry_context_reasons": []})
    @patch("app.oos_validation.forward_engine.get_replay_penalty", return_value={"total_adjustment": 0, "reasons": []})
    @patch("app.oos_validation.forward_engine.get_adaptive_replay_settings", return_value={"activation": 0.75, "pullback": 0.35, "stop_loss": -0.5})
    @patch("app.oos_validation.forward_engine.run_ai_replay_decision")
    @patch("app.oos_validation.forward_engine.build_market_snapshot")
    @patch("app.oos_validation.forward_engine._load_replay_entry_weights", return_value={})
    @patch("app.oos_validation.forward_engine._load_batch")
    def test_trade_closed_before_scored_window_is_not_journaled(
        self,
        load_batch,
        entry_weights,
        build_snapshot,
        decision,
        settings,
        penalty,
        entry_score,
        trade_context,
        fingerprint,
    ):
        manifest, data, paths = self._fixture()
        manifest["validation_window"]["start"] = "2026-09-12T14:00:00+00:00"
        load_batch.return_value = (manifest, data, paths)
        build_snapshot.side_effect = lambda row, previous: {
            "price": float(row["Close"]), "atr_percent": 1.0, "confidence": 60
        }
        decision.side_effect = [
            {"signal": "BUY", "strategy": "TEST"},
            {"signal": "HOLD", "strategy": "TEST"},
            {"signal": "HOLD", "strategy": "TEST"},
        ]

        result = run_forward_batch_replay("batch-002")
        self.assertEqual(result["total_trades"], 0)
        self.assertFalse(paths["journal"].exists())


if __name__ == "__main__":
    unittest.main()
