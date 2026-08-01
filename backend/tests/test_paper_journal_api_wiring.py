from pathlib import Path
import ast
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = BACKEND_ROOT / "app" / "main.py"


class PaperJournalApiWiringTests(unittest.TestCase):
    def setUp(self):
        self.source = MAIN_FILE.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def _imports_from(self, module_name):
        names = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                names.update(alias.name for alias in node.names)

        return names

    def test_journal_functions_are_not_imported_from_research_engine(self):
        research_imports = self._imports_from("app.research_engine")

        self.assertNotIn("save_trade_journal_entry", research_imports)
        self.assertNotIn("run_trade_journal", research_imports)
        self.assertNotIn("run_live_learning_feed", research_imports)

    def test_research_director_is_imported_from_modular_director(self):
        modular_imports = self._imports_from("app.research.director")
        legacy_imports = self._imports_from("app.research_engine")

        self.assertIn("run_research_director", modular_imports)
        self.assertNotIn("run_research_director", legacy_imports)

    def test_journal_functions_are_imported_from_canonical_repository(self):
        repository_imports = self._imports_from(
            "app.paper_trade_journal_repository"
        )

        self.assertIn("save_trade_journal_entry", repository_imports)
        self.assertIn("run_trade_journal", repository_imports)
        self.assertIn("run_live_learning_feed", repository_imports)

    def test_learning_feed_passes_research_director_explicitly(self):
        self.assertIn(
            "return run_canonical_live_learning_feed(run_research_director)",
            self.source,
        )

    def test_automatic_tracker_callback_does_not_write_second_journal_row(self):
        tracker_route = self.source.split(
            "def automatic_signal_tracker():",
            1,
        )[1].split(
            '@app.get("/api/ai-execution-engine")',
            1,
        )[0]

        self.assertIn("save_trade_function=lambda trade: trade", tracker_route)
        self.assertNotIn("save_trade_journal_entry(", tracker_route)

    def test_manual_and_simulated_close_routes_use_canonical_writer(self):
        manual_close = self.source.split(
            "def test_close_position():",
            1,
        )[1].split(
            '@app.get("/api/test-reset-position")',
            1,
        )[0]
        simulated_close = self.source.split(
            "def test_simulate_price",
            1,
        )[1].split(
            '@app.get("/api/quality-performance-summary")',
            1,
        )[0]

        self.assertIn("save_trade_journal_entry(", manual_close)
        self.assertIn("save_trade_journal_entry(", simulated_close)


if __name__ == "__main__":
    unittest.main()
