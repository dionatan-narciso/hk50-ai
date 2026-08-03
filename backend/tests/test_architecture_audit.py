from pathlib import Path
import ast
import tempfile
import unittest

from scripts.audit_architecture import (
    audit_critical_test_presence,
    inspect_imports,
    inspect_string_paths,
)


class ArchitectureAuditTests(unittest.TestCase):
    def _temporary_python_file(self, relative_path, source):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path, root

    def test_forbidden_legacy_symbols_are_errors(self):
        path, root = self._temporary_python_file(
            "app/example.py",
            "from app.research_engine import run_research_director\n",
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        import scripts.audit_architecture as audit
        original_root = audit.BACKEND_ROOT
        audit.BACKEND_ROOT = root
        self.addCleanup(setattr, audit, "BACKEND_ROOT", original_root)

        findings = inspect_imports(path, tree)

        self.assertTrue(any(
            finding.code == "FORBIDDEN_LEGACY_IMPORT"
            and finding.severity == "error"
            for finding in findings
        ))

    def test_allowed_source_loader_lab_import_is_not_warning(self):
        path, root = self._temporary_python_file(
            "app/research/source_loader.py",
            "from app.research_engine import run_strategy_lab\n",
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        import scripts.audit_architecture as audit
        original_root = audit.BACKEND_ROOT
        audit.BACKEND_ROOT = root
        self.addCleanup(setattr, audit, "BACKEND_ROOT", original_root)

        findings = inspect_imports(path, tree)

        self.assertEqual(findings, [])

    def test_unapproved_research_engine_import_is_warning(self):
        path, root = self._temporary_python_file(
            "app/example.py",
            "from app.research_engine import run_strategy_lab\n",
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        import scripts.audit_architecture as audit
        original_root = audit.BACKEND_ROOT
        audit.BACKEND_ROOT = root
        self.addCleanup(setattr, audit, "BACKEND_ROOT", original_root)

        findings = inspect_imports(path, tree)

        self.assertTrue(any(
            finding.code == "TRANSITIONAL_RESEARCH_ENGINE_IMPORT"
            and finding.severity == "warning"
            for finding in findings
        ))

    def test_hardcoded_runtime_path_is_warning(self):
        path, root = self._temporary_python_file(
            "app/example.py",
            'JOURNAL = "data/trade_journal.csv"\n',
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        import scripts.audit_architecture as audit
        original_root = audit.BACKEND_ROOT
        audit.BACKEND_ROOT = root
        self.addCleanup(setattr, audit, "BACKEND_ROOT", original_root)

        findings = inspect_string_paths(path, tree)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "HARDCODED_MUTABLE_PATH")

    def test_runtime_paths_definition_is_exempt(self):
        path, root = self._temporary_python_file(
            "app/runtime_paths.py",
            'JOURNAL = "trade_journal.csv"\n',
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        import scripts.audit_architecture as audit
        original_root = audit.BACKEND_ROOT
        audit.BACKEND_ROOT = root
        self.addCleanup(setattr, audit, "BACKEND_ROOT", original_root)

        self.assertEqual(inspect_string_paths(path, tree), [])

    def test_missing_critical_test_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            findings = audit_critical_test_presence(Path(temp_dir))

        self.assertTrue(any(
            finding.code == "CRITICAL_PATH_TEST_GAP"
            for finding in findings
        ))


if __name__ == "__main__":
    unittest.main()
