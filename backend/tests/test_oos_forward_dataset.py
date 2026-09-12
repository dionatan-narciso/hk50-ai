import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import pandas as pd

from app.oos_validation.forward_batches import build_batch_manifest, register_batch
from app.oos_validation.forward_dataset import build_next_batch_dataset, inspect_next_batch
from app.oos_validation.snapshot import freeze_candidate_snapshot


class ForwardOosDatasetTests(unittest.TestCase):
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
                        "win_rate": 50.0,
                        "average_return": 0.2,
                        "profit_factor": 1.5,
                        "fold_consistency_percent": 100.0,
                    }
                ],
            }
        )
        from app.oos_validation.snapshot import load_candidate_snapshot

        snapshot = load_candidate_snapshot()
        register_batch(
            build_batch_manifest(
                batch_id="batch-001",
                candidate_snapshot_sha256=snapshot["snapshot_sha256"],
                dataset_sha256="1" * 64,
                validation_start=datetime(2026, 8, 24, 8, 30, tzinfo=timezone.utc),
                validation_end=datetime(2026, 9, 12, 11, tzinfo=timezone.utc),
                scored_row_count=98,
                trade_count=4,
            )
        )

    def test_next_batch_waits_for_full_fourteen_day_window(self):
        plan = inspect_next_batch(now=datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.assertEqual(plan["status"], "not_ready")
        self.assertEqual(plan["batch_id"], "batch-002")
        self.assertEqual(plan["ready_at"], "2026-09-26T11:00:00+00:00")

    def test_next_batch_is_ready_at_exact_boundary(self):
        plan = inspect_next_batch(now=datetime(2026, 9, 26, 11, tzinfo=timezone.utc))
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["validation_window"]["start"], "2026-09-12T11:00:00+00:00")
        self.assertEqual(plan["validation_window"]["end"], "2026-09-26T11:00:00+00:00")

    def test_build_freezes_batch_with_continuity_history(self):
        calls = []

        def fake_download(symbol, **kwargs):
            calls.append((symbol, kwargs))
            index = pd.date_range(kwargs["start"], kwargs["end"], freq="1h", inclusive="left")
            return pd.DataFrame(
                {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5, "Volume": 10},
                index=index,
            )

        manifest = build_next_batch_dataset(
            now=datetime(2026, 9, 26, 11, tzinfo=timezone.utc),
            warmup_days=2,
            downloader=fake_download,
        )
        self.assertEqual(manifest["batch_id"], "batch-002")
        self.assertEqual(manifest["execution_start"], "2026-08-24T08:30:00+00:00")
        self.assertGreater(manifest["row_count"], manifest["scored_row_count"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "^HSI")

    def test_frozen_batch_refuses_different_replacement(self):
        def fake_download(symbol, **kwargs):
            index = pd.date_range(kwargs["start"], kwargs["end"], freq="1h", inclusive="left")
            return pd.DataFrame(
                {"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.5},
                index=index,
            )

        build_next_batch_dataset(
            now=datetime(2026, 9, 26, 11, tzinfo=timezone.utc),
            warmup_days=2,
            downloader=fake_download,
        )

        def changed_download(symbol, **kwargs):
            frame = fake_download(symbol, **kwargs)
            frame.iloc[-1, frame.columns.get_loc("Close")] = 999.0
            return frame

        with self.assertRaises(RuntimeError):
            build_next_batch_dataset(
                now=datetime(2026, 9, 26, 11, tzinfo=timezone.utc),
                warmup_days=2,
                downloader=changed_download,
            )


if __name__ == "__main__":
    unittest.main()
