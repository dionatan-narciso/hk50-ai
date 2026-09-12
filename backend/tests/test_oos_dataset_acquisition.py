import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import pandas as pd

from app.oos_validation.dataset import (
    build_default_validation_plan,
    fetch_validation_market_data,
    freeze_validation_dataset,
    inspect_discovery_bounds,
)
from app.oos_validation.snapshot import freeze_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


class OosDatasetAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

        paths = resolve_runtime_paths()
        paths.replay_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "opened_at": "2026-01-01T01:00:00+00:00",
                    "closed_at": "2026-01-01T04:00:00+00:00",
                    "return_percent": 0.5,
                },
                {
                    "opened_at": "2026-06-01T03:00:00+00:00",
                    "closed_at": "2026-06-01T08:00:00+00:00",
                    "return_percent": -0.2,
                },
            ]
        ).to_csv(paths.replay_trade_journal, index=False)

        freeze_candidate_snapshot(
            {
                "status": "completed",
                "total_trades": 2,
                "candidates": [
                    {
                        "classification": "PROMISING",
                        "direction": "POSITIVE",
                        "representative": {
                            "context": {"context_htf_trend_4h": "Neutral"}
                        },
                        "trades": 2,
                        "win_rate": 50.0,
                        "average_return": 0.15,
                        "profit_factor": 1.2,
                        "fold_consistency_percent": 100.0,
                    }
                ],
            }
        )

    def test_discovery_bounds_are_read_from_replay_journal(self):
        bounds = inspect_discovery_bounds()

        self.assertEqual(bounds.total_trades, 2)
        self.assertEqual(
            bounds.first_opened_at,
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            bounds.last_closed_at,
            datetime(2026, 6, 1, 8, tzinfo=timezone.utc),
        )

    def test_default_plan_places_oos_after_discovery_and_embargo(self):
        plan = build_default_validation_plan(
            validation_end=datetime(2026, 9, 1, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(
            plan.discovery.end,
            datetime(2026, 6, 1, 9, tzinfo=timezone.utc),
        )
        self.assertEqual(
            plan.validation.start,
            datetime(2026, 6, 8, 9, tzinfo=timezone.utc),
        )
        self.assertEqual(
            plan.validation.end,
            datetime(2026, 9, 1, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(plan.discovery.overlaps(plan.validation))

    def test_fetch_includes_warmup_but_scores_only_validation_window(self):
        plan = build_default_validation_plan(
            validation_end=datetime(2026, 6, 10, 12, tzinfo=timezone.utc)
        )
        calls = []

        def fake_download(symbol, **kwargs):
            calls.append((symbol, kwargs))
            index = pd.date_range(
                kwargs["start"],
                kwargs["end"],
                freq="1h",
                inclusive="left",
            )
            return pd.DataFrame(
                {
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.5,
                    "Volume": 10,
                },
                index=index,
            )

        data, warmup_start = fetch_validation_market_data(
            plan,
            warmup_days=2,
            downloader=fake_download,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "^HSI")
        self.assertEqual(warmup_start, plan.validation.start - pd.Timedelta(days=2))
        self.assertLess(data.index.min(), pd.Timestamp(plan.validation.start))
        self.assertGreaterEqual(
            len(data.loc[data.index >= pd.Timestamp(plan.validation.start)]),
            1,
        )
        self.assertLess(data.index.max(), pd.Timestamp(plan.validation.end))

    def test_frozen_dataset_is_validation_only_and_refuses_replacement(self):
        plan = build_default_validation_plan(
            validation_end=datetime(2026, 6, 10, 12, tzinfo=timezone.utc)
        )
        index = pd.date_range(
            plan.validation.start - pd.Timedelta(days=2),
            plan.validation.end,
            freq="1h",
            inclusive="left",
        )
        data = pd.DataFrame(
            {
                "Open": 100.0,
                "High": 101.0,
                "Low": 99.0,
                "Close": 100.5,
            },
            index=index,
        )
        paths = resolve_runtime_paths()
        replay_before = paths.replay_trade_journal.read_bytes()

        manifest = freeze_validation_dataset(
            plan,
            data,
            (plan.validation.start - pd.Timedelta(days=2)).to_pydatetime(),
        )

        self.assertTrue(paths.validation_market_data.exists())
        self.assertTrue(paths.validation_dataset_manifest.exists())
        self.assertEqual(paths.replay_trade_journal.read_bytes(), replay_before)
        self.assertFalse(paths.paper_dir.exists())
        self.assertFalse(paths.live_dir.exists())
        self.assertGreater(manifest["row_count"], manifest["scored_row_count"])

        same = freeze_validation_dataset(
            plan,
            data,
            (plan.validation.start - pd.Timedelta(days=2)).to_pydatetime(),
        )
        self.assertEqual(same["dataset_sha256"], manifest["dataset_sha256"])

        changed = data.copy()
        changed.iloc[-1, changed.columns.get_loc("Close")] = 999.0
        with self.assertRaises(RuntimeError):
            freeze_validation_dataset(
                plan,
                changed,
                (plan.validation.start - pd.Timedelta(days=2)).to_pydatetime(),
            )

    def test_invalid_discovery_timestamp_is_rejected(self):
        paths = resolve_runtime_paths()
        pd.DataFrame(
            [{"opened_at": "bad", "closed_at": "2026-01-01T01:00:00Z"}]
        ).to_csv(paths.replay_trade_journal, index=False)

        with self.assertRaises(ValueError):
            inspect_discovery_bounds()


if __name__ == "__main__":
    unittest.main()
