import os
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.oos_validation.engine import run_oos_validation_replay
from app.runtime_paths import resolve_runtime_paths


class OosValidationEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

        paths = resolve_runtime_paths()
        paths.replay_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [{"learning_type": "strategy", "key": "RSI < 30", "score_adjustment": 0}]
        ).to_csv(paths.replay_learning_memory, index=False)
        pd.DataFrame([{"learning_strength": 1.0}]).to_csv(
            paths.replay_learning_control, index=False
        )
        pd.DataFrame(
            [
                {
                    "rsi_rising_bonus": 5,
                    "rsi_falling_penalty": -5,
                    "negative_candle_penalty": -3,
                    "ma20_stretch_bonus": 2,
                    "ma50_stretch_bonus": 2,
                    "extreme_rsi_penalty": -3,
                }
            ]
        ).to_csv(paths.replay_entry_learning_memory, index=False)

    def test_warmup_cannot_open_trades_and_replay_state_is_read_only(self):
        paths = resolve_runtime_paths()
        replay_sentinels = {
            path: path.read_bytes()
            for path in (
                paths.replay_learning_memory,
                paths.replay_learning_control,
                paths.replay_entry_learning_memory,
            )
        }
        index = pd.to_datetime(
            [
                "2026-08-24T07:30:00Z",
                "2026-08-24T08:30:00Z",
                "2026-08-24T09:30:00Z",
            ]
        )
        data = pd.DataFrame(
            {
                "Open": [100.0, 100.0, 99.0],
                "High": [101.0, 101.0, 100.0],
                "Low": [99.0, 99.0, 98.0],
                "Close": [100.0, 100.0, 99.0],
                "MA20": [100.0, 100.0, 100.0],
                "MA50": [101.0, 101.0, 101.0],
                "RSI": [25.0, 25.0, 25.0],
                "ATR": [1.0, 1.0, 1.0],
                "ATR_PERCENT": [0.5, 0.5, 0.5],
            },
            index=index,
        )
        manifest = {
            "candidate_snapshot_sha256": "candidate-hash",
            "dataset_sha256": "dataset-hash",
            "validation_window": {
                "start": "2026-08-24T08:30:00+00:00",
                "end": "2026-08-24T10:30:00+00:00",
            },
        }

        def fake_snapshot(row, previous_row=None):
            return {
                "price": float(row["Close"]),
                "close": float(row["Close"]),
                "previous_close": float(row["Close"]),
                "rsi": 25.0,
                "previous_rsi": 24.0,
                "ma20": 100.0,
                "ma50": 101.0,
                "atr_percent": 0.5,
                "trend": "Bearish",
                "risk": "Low",
                "confidence": 70,
            }

        decision = {
            "strategy": "RSI < 30",
            "original_strategy": "RSI < 30",
            "signal": "BUY",
            "reason": "test",
            "market_regime": "UNKNOWN",
            "volatility_regime": "UNKNOWN",
            "rotation_changed": False,
            "rotation_reason": None,
        }
        trade_context = {
            "close_at_entry": 100.0,
            "ma20_at_entry": 100.0,
            "ma50_at_entry": 101.0,
            "distance_ma20": 0.0,
            "distance_ma50": -1.0,
            "previous_candle_return": 0.0,
            "trend_strength": "WEAK",
            "ma_alignment": "BEARISH",
            "rsi_slope": "RISING",
        }

        with patch("app.oos_validation.engine._load_manifest", return_value=manifest), patch(
            "app.oos_validation.engine._load_market_data", return_value=data
        ), patch(
            "app.oos_validation.engine.build_market_snapshot", side_effect=fake_snapshot
        ), patch(
            "app.oos_validation.engine.run_ai_replay_decision", return_value=decision
        ), patch(
            "app.oos_validation.engine.get_replay_penalty",
            return_value={"total_adjustment": 0, "reasons": []},
        ), patch(
            "app.oos_validation.engine.calculate_trade_context", return_value=trade_context
        ), patch(
            "app.oos_validation.engine.calculate_entry_context_score",
            return_value={"entry_context_adjustment": 0, "entry_context_reasons": []},
        ), patch(
            "app.oos_validation.engine.derive_replay_higher_timeframe_context",
            return_value=SimpleNamespace(
                trend_4h="Neutral",
                trend_1d="Neutral",
                agreement="NEUTRAL",
                aligned_direction=None,
            ),
        ):
            summary = run_oos_validation_replay()

        self.assertEqual(summary["total_trades"], 1)
        journal = pd.read_csv(paths.validation_trade_journal)
        self.assertEqual(len(journal), 1)
        opened = pd.to_datetime(journal.iloc[0]["opened_at"], utc=True)
        self.assertGreaterEqual(opened, pd.Timestamp(manifest["validation_window"]["start"]))
        self.assertEqual(journal.iloc[0]["context_htf_trend_4h"], "Neutral")
        for path, before in replay_sentinels.items():
            self.assertEqual(path.read_bytes(), before)
        self.assertFalse(paths.paper_dir.exists())
        self.assertFalse(paths.live_dir.exists())


if __name__ == "__main__":
    unittest.main()
