import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.runtime_paths import resolve_runtime_paths
from app.voting_performance_memory import (
    get_vote_strength_win_rate,
    get_voting_memory_file,
    load_voting_performance_memory,
    save_voting_result,
    summarise_voting_performance,
)


class VotingPerformanceMemoryPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name) / "runtime-data"
        self.env_patch = patch.dict(
            os.environ,
            {"HK50_DATA_DIR": str(self.data_root)},
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_voting_memory_path_uses_configured_paper_directory(self):
        paths = resolve_runtime_paths()

        self.assertEqual(
            get_voting_memory_file(),
            paths.paper_voting_performance_memory,
        )
        self.assertTrue(
            str(get_voting_memory_file()).startswith(str(paths.paper_dir))
        )

    def test_save_and_load_use_only_paper_voting_memory(self):
        paths = resolve_runtime_paths()

        save_voting_result(
            vote_signal="BUY",
            vote_strength=4,
            total_votes=4,
            strategy_signal="BUY",
            final_signal="BUY",
            trade_result=1.25,
        )

        rows = load_voting_performance_memory()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vote_strength"], 4)
        self.assertEqual(rows[0]["trade_result"], 1.25)
        self.assertTrue(rows[0]["won"])
        self.assertTrue(paths.paper_voting_performance_memory.exists())
        self.assertFalse((paths.replay_dir / "voting_performance_memory.csv").exists())
        self.assertFalse((paths.live_dir / "voting_performance_memory.csv").exists())

    def test_summary_calculations_are_preserved(self):
        save_voting_result("BUY", 4, 4, "BUY", "BUY", 1.0)
        save_voting_result("BUY", 4, 4, "BUY", "BUY", -0.5)
        save_voting_result("SELL", 3, 4, "SELL", "SELL", 2.0)

        summary = summarise_voting_performance()

        self.assertEqual(summary["total_records"], 3)
        strength_four = next(
            row for row in summary["summary"]
            if row["vote_strength"] == 4
        )
        self.assertEqual(strength_four["total_trades"], 2)
        self.assertEqual(strength_four["wins"], 1)
        self.assertEqual(strength_four["losses"], 1)
        self.assertEqual(strength_four["win_rate"], 50.0)
        self.assertEqual(strength_four["average_return"], 0.25)
        self.assertEqual(summary["best_vote_strength"], 3)
        self.assertEqual(summary["best_win_rate"], 100.0)
        self.assertEqual(get_vote_strength_win_rate(4), 50.0)

    def test_legacy_unscoped_voting_memory_is_ignored(self):
        legacy_path = Path("backend/data/voting_performance_memory.csv")
        legacy_path.parent.mkdir(parents=True, exist_ok=True)

        original_content = None
        if legacy_path.exists():
            original_content = legacy_path.read_bytes()

        try:
            with legacy_path.open("w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "vote_signal",
                    "vote_strength",
                    "total_votes",
                    "strategy_signal",
                    "final_signal",
                    "trade_result",
                    "won",
                ])
                writer.writerow(["BUY", 5, 5, "BUY", "BUY", 9.0, True])

            rows = load_voting_performance_memory()
            self.assertEqual(rows, [])
        finally:
            if original_content is None:
                legacy_path.unlink(missing_ok=True)
            else:
                legacy_path.write_bytes(original_content)


if __name__ == "__main__":
    unittest.main()
