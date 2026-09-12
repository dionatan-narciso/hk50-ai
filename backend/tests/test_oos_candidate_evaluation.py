import json
import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.oos_validation.evaluation import evaluate_frozen_candidates
from app.oos_validation.snapshot import freeze_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


class OosCandidateEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

        freeze_candidate_snapshot(
            {
                "status": "completed",
                "total_trades": 20,
                "candidates": [
                    {
                        "classification": "PROMISING",
                        "direction": "POSITIVE",
                        "representative": {
                            "context": {"context_htf_trend_4h": "Neutral"}
                        },
                        "trades": 12,
                        "win_rate": 60.0,
                        "average_return": 0.3,
                        "profit_factor": 2.0,
                        "fold_consistency_percent": 100.0,
                    },
                    {
                        "classification": "PROMISING",
                        "direction": "NEGATIVE",
                        "representative": {
                            "context": {"context_price_position": "BETWEEN_MAS"}
                        },
                        "trades": 10,
                        "win_rate": 20.0,
                        "average_return": -0.4,
                        "profit_factor": 0.3,
                        "fold_consistency_percent": 100.0,
                    },
                    {
                        "classification": "WATCH",
                        "direction": "POSITIVE",
                        "representative": {
                            "context": {"context_trend_strength": "STRONG"}
                        },
                        "trades": 9,
                        "win_rate": 55.0,
                        "average_return": 0.2,
                        "profit_factor": 1.5,
                        "fold_consistency_percent": 100.0,
                    },
                ],
            }
        )

    def _write_journal(self):
        paths = resolve_runtime_paths()
        paths.validation_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for value in [0.4, 0.3, 0.2, -0.1, 0.5]:
            rows.append(
                {
                    "return_percent": value,
                    "context_htf_trend_4h": "Neutral",
                    "context_price_position": "BELOW_BOTH",
                    "context_trend_strength": "MODERATE",
                }
            )
        for value in [0.2, 0.1, -0.1, 0.3, 0.2]:
            rows.append(
                {
                    "return_percent": value,
                    "context_htf_trend_4h": "Bearish",
                    "context_price_position": "BETWEEN_MAS",
                    "context_trend_strength": "WEAK",
                }
            )
        rows.extend(
            [
                {
                    "return_percent": 0.8,
                    "context_htf_trend_4h": "Bullish",
                    "context_price_position": "ABOVE_BOTH",
                    "context_trend_strength": "STRONG",
                },
                {
                    "return_percent": -0.2,
                    "context_htf_trend_4h": "Bullish",
                    "context_price_position": "ABOVE_BOTH",
                    "context_trend_strength": "STRONG",
                },
            ]
        )
        pd.DataFrame(rows).to_csv(paths.validation_trade_journal, index=False)

    def test_positive_candidate_passes_when_oos_sign_persists(self):
        self._write_journal()
        report = evaluate_frozen_candidates(run_replay=False)
        candidate = next(
            item
            for item in report["candidates"]
            if item["context"] == {"context_htf_trend_4h": "Neutral"}
        )
        self.assertEqual(candidate["validation"]["trades"], 5)
        self.assertEqual(candidate["oos_status"], "PASS")
        self.assertGreater(candidate["effect_retention_ratio"], 0)

    def test_negative_candidate_fails_when_oos_sign_reverses(self):
        self._write_journal()
        report = evaluate_frozen_candidates(run_replay=False)
        candidate = next(
            item
            for item in report["candidates"]
            if item["context"] == {"context_price_position": "BETWEEN_MAS"}
        )
        self.assertEqual(candidate["validation"]["trades"], 5)
        self.assertEqual(candidate["oos_status"], "FAIL")
        self.assertIsNone(candidate["effect_retention_ratio"])

    def test_small_oos_sample_is_inconclusive(self):
        self._write_journal()
        report = evaluate_frozen_candidates(run_replay=False)
        candidate = next(
            item
            for item in report["candidates"]
            if item["context"] == {"context_trend_strength": "STRONG"}
        )
        self.assertEqual(candidate["validation"]["trades"], 2)
        self.assertEqual(candidate["oos_status"], "INCONCLUSIVE")

    def test_report_is_written_only_to_validation_namespace(self):
        self._write_journal()
        report = evaluate_frozen_candidates(run_replay=False)
        paths = resolve_runtime_paths()
        self.assertTrue(paths.validation_result_report.exists())
        saved = json.loads(paths.validation_result_report.read_text(encoding="utf-8"))
        self.assertEqual(saved["status_counts"], report["status_counts"])
        self.assertFalse(paths.paper_dir.exists())
        self.assertFalse(paths.live_dir.exists())


if __name__ == "__main__":
    unittest.main()
