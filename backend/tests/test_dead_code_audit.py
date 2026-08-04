import tempfile
import unittest
from pathlib import Path

from scripts.audit_dead_code import (
    BACKEND_ROOT,
    collect_dead_code_candidates,
    collect_unused_imports,
    run_audit,
)


class DeadCodeAuditTests(unittest.TestCase):
    def make_file(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_reports_unreferenced_private_function(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            module = self.make_file(root, "app/sample.py", "def _unused():\n    return 1\n")

            candidates = collect_dead_code_candidates([module], [module])

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].name, "_unused")
            self.assertEqual(candidates[0].confidence, "medium")

    def test_does_not_report_called_function(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            module = self.make_file(
                root,
                "app/sample.py",
                "def helper():\n    return 1\n\ndef caller():\n    return helper()\n",
            )

            candidates = collect_dead_code_candidates([module], [module])

            self.assertNotIn("helper", {item.name for item in candidates})

    def test_does_not_report_imported_function(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            source = self.make_file(root, "app/source.py", "def service():\n    return 1\n")
            consumer = self.make_file(
                root,
                "app/consumer.py",
                "from app.source import service\n\ndef use():\n    return service()\n",
            )

            candidates = collect_dead_code_candidates([source, consumer], [source, consumer])

            self.assertNotIn("service", {item.name for item in candidates})

    def test_does_not_report_fastapi_decorated_endpoint(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            module = self.make_file(
                root,
                "app/api.py",
                "class App:\n    def get(self, path):\n        return lambda fn: fn\n\napp = App()\n\n@app.get('/health')\ndef health():\n    return {'ok': True}\n",
            )

            candidates = collect_dead_code_candidates([module], [module])

            self.assertNotIn("health", {item.name for item in candidates})

    def test_reports_unused_import(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            module = self.make_file(root, "app/sample.py", "import os\n\ndef value():\n    return 1\n")

            candidates = collect_unused_imports([module])

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].name, "os")
            self.assertEqual(candidates[0].confidence, "high")

    def test_does_not_report_used_import(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_ROOT) as temp:
            root = Path(temp)
            module = self.make_file(
                root,
                "app/sample.py",
                "from pathlib import Path\n\ndef current():\n    return Path('.')\n",
            )

            candidates = collect_unused_imports([module])

            self.assertEqual(candidates, [])

    def test_run_audit_reports_parse_errors_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            backend = Path(temp)
            self.make_file(backend, "app/broken.py", "def broken(:\n")

            report = run_audit(backend)

            self.assertEqual(report["status"], "failed")
            self.assertEqual(len(report["parse_errors"]), 1)


if __name__ == "__main__":
    unittest.main()
