import json
import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import pandas as pd

from app.oos_validation.forward_batches import build_batch_manifest, register_batch
from app.oos_validation.forward_dataset import get_batch_paths
from app.oos_validation.forward_evaluation import evaluate_and_register_forward_batch
from app.oos_validation.snapshot import freeze_candidate_snapshot, load_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


class ForwardOosEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

        freeze_candidate_snapshot(
            {
                "status": "completed",
                "total_trades": 10,
                "candidates": [
                    {
                        "classification": "PROMISING",
                        "direction": "POSITIVE",
                        "representative": {"context": {"context_session": "ASIA"}},
                        "trades": 10,
                        "win_rate": 60.0,
                        "average_return": 0.2,
                        "profit_factor": 1.5,
                        "fold_consistency_percent": 100.0,
                    }
                ],
            }
        )
        snapshot = load_candidate_snapshot()
        register_batch(
            build_batch_manifest(
                batch_id="batch-001",
                candidate_snapshot_sha256=snapshot["snapshot_sha256"],
                dataset_sha256="1" * 64,
                validation_start=datetime(2026, 8, 24, tzinfo=timezone.utc),
                validation_end=datetime(2026, 9, 12, tzinfo=timezone.utc),
                scored_row_count=50,
                trade_count=3,
            )
        )
        paths = resolve_runtime_paths()
        paths.validation_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {"return_percent": 0.2, "context_session": "ASIA"},
                {"return_percent": -0.1, "context_session": "ASIA"},
                {"return_percent": 0.3, "context_session": "ASIA"},
            ]
        ).to_csv(paths.validation_trade_journal, index=False)

        batch_paths = get_batch_paths("batch-002")
        batch_paths["folder"].mkdir(parents=True, exist_ok=True)
        manifest = {
            "batch_id": "batch-002",
            "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
            "dataset_sha256": "2" * 64,
            "scored_row_count": 40,
            "validation_window": {
                "start": "2026-09-12T00:00:00+00:00",
                "end": "2026-09-26T00:00:00+00:00",
            },
        }
        batch_paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
        pd.DataFrame(
            [
                {"return_percent": 0.4, "context_session": "ASIA"},
                {"return_percent": 0.1, "context_session": "ASIA"},
            ]
        ).to_csv(batch_paths["journal"], index=False)

    @patch("app.oos_validation.forward_evaluation.run_forward_batch_replay")
    def test_cumulative_evidence_combines_batch_one_and_current_batch(self, replay):
        replay.return_value = {
            "status": "completed",
            "total_trades": 2,
            "wins": 2,
            "losses": 0,
        }
        report = evaluate_and_register_forward_batch("batch-002")
        candidate = report["cumulative"]["candidates"][0]
        self.assertEqual(report["registered_batch_count"], 2)
        self.assertEqual(report["cumulative"]["baseline"]["trades"], 5)
        self.assertEqual(candidate["validation"]["trades"], 5)
        self.assertEqual(candidate["evidence_level"], "PRELIMINARY")

    @patch("app.oos_validation.forward_evaluation.run_forward_batch_replay")
    def test_registration_is_tied_to_frozen_dataset_hash(self, replay):
        replay.return_value = {"status": "completed", "total_trades": 2}
        report = evaluate_and_register_forward_batch("batch-002")
        registry_path = resolve_runtime_paths().validation_dir / "forward_batches" / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(registry["batches"][-1]["dataset_sha256"], "2" * 64)
        self.assertEqual(report["candidate_snapshot_sha256"], load_candidate_snapshot()["snapshot_sha256"])

    @patch("app.oos_validation.forward_evaluation.run_forward_batch_replay")
    def test_mismatched_candidate_snapshot_is_rejected(self, replay):
        replay.return_value = {"status": "completed", "total_trades": 2}
        paths = get_batch_paths("batch-002")
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        manifest["candidate_snapshot_sha256"] = "f" * 64
        paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            evaluate_and_register_forward_batch("batch-002")


if __name__ == "__main__":
    unittest.main()
