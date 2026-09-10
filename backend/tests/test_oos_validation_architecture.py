import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from app.oos_validation.contracts import ValidationPlan, ValidationWindow
from app.oos_validation.repository import append_validation_trade, reset_validation_journal
from app.oos_validation.snapshot import (
    build_candidate_snapshot,
    freeze_candidate_snapshot,
    load_candidate_snapshot,
)
from app.runtime_paths import resolve_runtime_paths


class OosValidationArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(
            os.environ,
            {"HK50_DATA_DIR": str(self.root / "runtime-data")},
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def _report(self, average_return=0.25):
        return {
            "status": "completed",
            "total_trades": 84,
            "candidates": [
                {
                    "classification": "PROMISING",
                    "direction": "POSITIVE",
                    "representative": {
                        "context": {
                            "context_trend_strength": "STRONG",
                            "context_htf_trend_1d": "Bearish",
                        }
                    },
                    "trades": 18,
                    "win_rate": 61.11,
                    "average_return": average_return,
                    "profit_factor": 2.8,
                    "fold_consistency_percent": 100.0,
                },
                {
                    "classification": "REJECT",
                    "direction": "NEGATIVE",
                    "representative": {
                        "context": {"context_session": "QUIET"}
                    },
                    "trades": 5,
                    "win_rate": 20.0,
                    "average_return": -0.1,
                    "profit_factor": 0.5,
                    "fold_consistency_percent": 33.33,
                },
            ],
        }

    def test_validation_namespace_is_separate_from_replay_and_paper(self):
        paths = resolve_runtime_paths()
        self.assertNotEqual(paths.validation_dir, paths.replay_dir)
        self.assertNotEqual(paths.validation_dir, paths.paper_dir)
        self.assertEqual(paths.validation_trade_journal.parent, paths.validation_dir)
        self.assertEqual(paths.validation_candidate_snapshot.parent, paths.validation_dir)

    def test_validation_journal_cannot_touch_replay_or_paper_state(self):
        paths = resolve_runtime_paths()
        paths.replay_trade_journal.parent.mkdir(parents=True, exist_ok=True)
        paths.paper_trade_journal.parent.mkdir(parents=True, exist_ok=True)
        paths.replay_trade_journal.write_text("replay-sentinel", encoding="utf-8")
        paths.paper_trade_journal.write_text("paper-sentinel", encoding="utf-8")

        append_validation_trade({"strategy": "RSI < 30", "return_percent": 0.5})
        journal = pd.read_csv(paths.validation_trade_journal)

        self.assertEqual(len(journal), 1)
        self.assertEqual(paths.replay_trade_journal.read_text(encoding="utf-8"), "replay-sentinel")
        self.assertEqual(paths.paper_trade_journal.read_text(encoding="utf-8"), "paper-sentinel")

        reset_validation_journal()
        self.assertFalse(paths.validation_trade_journal.exists())
        self.assertTrue(paths.replay_trade_journal.exists())
        self.assertTrue(paths.paper_trade_journal.exists())

    def test_dataset_plan_rejects_overlap(self):
        discovery = ValidationWindow(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        validation = ValidationWindow(
            datetime(2024, 12, 1, tzinfo=timezone.utc),
            datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            ValidationPlan("HK50", "1h", discovery, validation)

    def test_dataset_plan_accepts_strictly_separate_windows(self):
        discovery = ValidationWindow(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        validation = ValidationWindow(
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        plan = ValidationPlan("HK50", "1h", discovery, validation)
        self.assertFalse(plan.discovery.overlaps(plan.validation))

    def test_candidate_snapshot_is_deterministic_and_filters_rejected_rows(self):
        first = build_candidate_snapshot(self._report())
        second = build_candidate_snapshot(self._report())
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_count"], 1)
        self.assertEqual(first["discovery_total_trades"], 84)
        self.assertEqual(len(first["snapshot_sha256"]), 64)

    def test_candidate_freeze_is_idempotent_but_refuses_retuning(self):
        path = freeze_candidate_snapshot(self._report())
        original = path.read_text(encoding="utf-8")
        freeze_candidate_snapshot(self._report())
        self.assertEqual(path.read_text(encoding="utf-8"), original)

        with self.assertRaises(RuntimeError):
            freeze_candidate_snapshot(self._report(average_return=0.5))

    def test_snapshot_integrity_detects_manual_change(self):
        path = freeze_candidate_snapshot(self._report())
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        snapshot["candidates"][0]["discovery_average_return"] = 99.0
        path.write_text(json.dumps(snapshot), encoding="utf-8")

        with self.assertRaises(ValueError):
            load_candidate_snapshot()


if __name__ == "__main__":
    unittest.main()
