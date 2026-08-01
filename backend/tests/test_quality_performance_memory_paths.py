import csv
import os
import tempfile
import unittest
from pathlib import Path

from app.quality_performance_memory import (
    get_quality_analytics_bonus,
    get_quality_memory_file,
    get_quality_performance_summary,
    update_quality_performance_memory,
)


class QualityPerformanceMemoryPathTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = os.environ.get("HK50_DATA_DIR")
        os.environ["HK50_DATA_DIR"] = self.temp_dir.name

    def tearDown(self):
        if self.original_data_dir is None:
            os.environ.pop("HK50_DATA_DIR", None)
        else:
            os.environ["HK50_DATA_DIR"] = self.original_data_dir
        self.temp_dir.cleanup()

    def test_quality_memory_uses_configured_paper_directory(self):
        path = get_quality_memory_file()
        self.assertEqual(path, Path(self.temp_dir.name).resolve() / "paper" / "quality_performance_memory.csv")

    def test_updates_and_summary_preserve_existing_calculations(self):
        update_quality_performance_memory("STRONG", 1.0)
        update_quality_performance_memory("STRONG", 0.5)
        update_quality_performance_memory("STRONG", -0.5)

        summary = get_quality_performance_summary()
        row = summary["quality_rows"][0]

        self.assertEqual(summary["status"], "ready")
        self.assertEqual(summary["best_quality"], "STRONG")
        self.assertEqual(int(row["total_trades"]), 3)
        self.assertEqual(int(row["wins"]), 2)
        self.assertEqual(int(row["losses"]), 1)
        self.assertEqual(float(row["avg_return"]), 0.333)
        self.assertEqual(float(row["best_return"]), 1.0)
        self.assertEqual(float(row["worst_return"]), -0.5)
        self.assertEqual(float(row["win_rate"]), 66.67)

    def test_bonus_thresholds_are_unchanged(self):
        for value in (1.0, 0.8, 0.6):
            update_quality_performance_memory("EXCEPTIONAL", value)

        result = get_quality_analytics_bonus("EXCEPTIONAL")
        self.assertEqual(result["analytics_bonus"], 5)
        self.assertEqual(result["reason"], "Quality level has strong historical performance")

    def test_legacy_and_replay_files_are_ignored(self):
        root = Path(self.temp_dir.name)
        legacy = root / "quality_performance_memory.csv"
        replay = root / "replay" / "quality_performance_memory.csv"
        replay.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            "quality", "total_trades", "wins", "losses",
            "avg_return", "best_return", "worst_return",
        ]
        for path in (legacy, replay):
            with path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "quality": "LEGACY",
                    "total_trades": 10,
                    "wins": 10,
                    "losses": 0,
                    "avg_return": 9,
                    "best_return": 9,
                    "worst_return": 9,
                })

        summary = get_quality_performance_summary()
        self.assertEqual(summary["status"], "empty")


if __name__ == "__main__":
    unittest.main()
