import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from app.replay_context_candidates import build_context_candidate_report
from app.replay_journal_repository import get_replay_journal_path


class ReplayContextCandidateTests(unittest.TestCase):
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

    def _write(self, rows):
        path = get_replay_journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(path, index=False)

    def test_exact_same_trade_membership_is_deduplicated(self):
        rows = []
        for i, value in enumerate([0.5, 0.4, 0.3, 0.2, 0.6, 0.5, 0.4, 0.3]):
            rows.append({
                "opened_at": f"2026-01-{i + 1:02d}T00:00:00+00:00",
                "return_percent": value,
                "context_trend_strength": "STRONG",
                "context_htf_agreement": "NEUTRAL",
            })
        self._write(rows)

        result = build_context_candidate_report(min_trades=8, max_dimensions=2, folds=2)

        self.assertLess(result["distinct_candidate_count"], result["raw_pattern_count"])
        candidate = result["candidates"][0]
        self.assertGreater(candidate["equivalent_pattern_count"], 1)
        self.assertEqual(candidate["matched_trade_count"], 8)

    def test_prefers_simpler_representative_for_same_membership(self):
        rows = []
        for i in range(8):
            rows.append({
                "opened_at": f"2026-02-{i + 1:02d}T00:00:00+00:00",
                "return_percent": 0.4,
                "context_trend_strength": "STRONG",
                "context_htf_agreement": "NEUTRAL",
            })
        self._write(rows)

        result = build_context_candidate_report(min_trades=8, max_dimensions=2, folds=2)
        candidate = result["candidates"][0]

        self.assertEqual(len(candidate["representative"]["dimensions"]), 1)

    def test_large_robust_effect_is_promising(self):
        rows = []
        for i in range(12):
            rows.append({
                "opened_at": f"2026-03-{i + 1:02d}T00:00:00+00:00",
                "return_percent": 0.3,
                "context_trend_strength": "STRONG",
            })
        self._write(rows)

        result = build_context_candidate_report(min_trades=8, max_dimensions=1, folds=3)

        self.assertEqual(result["promising"][0]["classification"], "PROMISING")
        self.assertEqual(result["promising"][0]["direction"], "POSITIVE")

    def test_small_robust_sample_is_watch(self):
        rows = []
        for i in range(8):
            rows.append({
                "opened_at": f"2026-04-{i + 1:02d}T00:00:00+00:00",
                "return_percent": -0.4,
                "context_price_position": "BETWEEN_MAS",
            })
        self._write(rows)

        result = build_context_candidate_report(min_trades=8, max_dimensions=1, folds=2)

        self.assertEqual(result["watch"][0]["classification"], "WATCH")
        self.assertEqual(result["watch"][0]["direction"], "NEGATIVE")

    def test_inconsistent_pattern_is_rejected(self):
        returns = [0.5, 0.4, 0.3, 0.2, -0.8, -0.7, -0.6, -0.5]
        rows = []
        for i, value in enumerate(returns):
            rows.append({
                "opened_at": f"2026-05-{i + 1:02d}T00:00:00+00:00",
                "return_percent": value,
                "context_trend_strength": "WEAK",
            })
        self._write(rows)

        result = build_context_candidate_report(min_trades=8, max_dimensions=1, folds=2)

        self.assertEqual(result["candidates"][0]["classification"], "REJECT")

    def test_no_data_is_preserved(self):
        result = build_context_candidate_report()
        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
