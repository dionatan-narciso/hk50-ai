import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.research.research_results_repository import (
    append_research_results,
    get_research_results_path,
    load_research_results,
)
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class ResearchResultsRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {DATA_ROOT_ENV_VAR: str(self.data_root)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def _row(self, strategy, total_return):
        return {
            "timestamp": "2026-08-04 12:00:00",
            "lab_type": "Strategy Lab",
            "rank": 1,
            "strategy": strategy,
            "trades": 10,
            "win_rate": 60,
            "profit_factor": 1.5,
            "total_return": total_return,
            "average_trade": 0.2,
            "max_drawdown": -1.0,
            "signal": "BUY",
        }

    def test_path_resolves_inside_paper_directory(self):
        paths = resolve_runtime_paths()
        self.assertEqual(get_research_results_path(), paths.paper_research_results)
        self.assertEqual(get_research_results_path().parent, paths.paper_dir)

    def test_append_and_load_preserve_existing_csv_contract(self):
        append_research_results([self._row("RSI", 1.2)])
        append_research_results([self._row("Breakout", -0.4)])

        frame = load_research_results()
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame["strategy"].tolist(), ["RSI", "Breakout"])
        self.assertEqual(frame["total_return"].tolist(), [1.2, -0.4])

    def test_legacy_unscoped_research_results_are_ignored(self):
        legacy = self.data_root / "research_results.csv"
        pd.DataFrame([self._row("LEGACY", 99)]).to_csv(legacy, index=False)

        frame = load_research_results()
        self.assertTrue(frame.empty)

    def test_repository_does_not_create_replay_or_live_state(self):
        append_research_results([self._row("RSI", 1.2)])
        paths = resolve_runtime_paths()

        self.assertTrue(paths.paper_research_results.exists())
        self.assertFalse((paths.replay_dir / "research_results.csv").exists())
        self.assertFalse((paths.live_dir / "research_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
