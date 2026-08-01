import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.live_performance_memory import (
    get_strategy_performance_bonus,
    get_strategy_performance_path,
    load_live_strategy_performance,
    summarise_live_strategy_performance,
    update_live_strategy_memory,
)
from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


class StrategyPerformanceMemoryPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {DATA_ROOT_ENV_VAR: str(self.data_root)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_path_resolves_inside_paper_directory(self):
        paths = resolve_runtime_paths()
        self.assertEqual(get_strategy_performance_path(), paths.paper_strategy_performance_memory)
        self.assertEqual(get_strategy_performance_path().parent, paths.paper_dir)

    def test_updates_and_reads_only_configured_paper_memory(self):
        update_live_strategy_memory("RSI < 30", 1.0)
        update_live_strategy_memory("RSI < 30", -0.5)

        df = load_live_strategy_performance()
        row = df.iloc[0]

        self.assertEqual(row["strategy"], "RSI < 30")
        self.assertEqual(int(row["total_trades"]), 2)
        self.assertEqual(int(row["wins"]), 1)
        self.assertEqual(int(row["losses"]), 1)
        self.assertAlmostEqual(float(row["average_return"]), 0.25)

        paths = resolve_runtime_paths()
        self.assertFalse((paths.replay_dir / "live_strategy_performance.csv").exists())
        self.assertFalse((paths.live_dir / "live_strategy_performance.csv").exists())

    def test_legacy_file_is_ignored(self):
        legacy = self.data_root / "live_strategy_performance.csv"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{
            "strategy": "LEGACY",
            "wins": 10,
            "losses": 0,
            "total_trades": 10,
            "win_rate": 100,
            "average_return": 5,
        }]).to_csv(legacy, index=False)

        summary = summarise_live_strategy_performance()
        self.assertEqual(summary["total_strategies"], 0)

    def test_score_and_bonus_calculations_are_preserved(self):
        for trade_return in [1.0, 1.0, 1.0]:
            update_live_strategy_memory("Strong", trade_return)

        summary = summarise_live_strategy_performance()
        strategy = summary["strategies"][0]

        self.assertEqual(strategy["win_rate"], 100.0)
        self.assertEqual(strategy["live_score"], 75.0)

        bonus = get_strategy_performance_bonus("Strong")
        self.assertEqual(bonus["strategy_performance_bonus"], 8)
        self.assertEqual(bonus["reason"], "Strong live strategy performance")


if __name__ == "__main__":
    unittest.main()
