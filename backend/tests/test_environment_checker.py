from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.check_environment import (
    check_data_root_write_access,
    check_imports,
    check_python_version,
    check_runtime_path_isolation,
    run_environment_checks,
)


class EnvironmentCheckerTests(unittest.TestCase):
    def test_python_version_accepts_supported_versions(self):
        result = check_python_version(SimpleNamespace(major=3, minor=12, micro=0))
        self.assertTrue(result["passed"])

    def test_python_version_rejects_unsupported_versions(self):
        result = check_python_version(SimpleNamespace(major=3, minor=11, micro=9))
        self.assertFalse(result["passed"])

    def test_import_check_reports_missing_module(self):
        with patch(
            "scripts.check_environment.importlib.import_module",
            side_effect=ModuleNotFoundError("missing dependency"),
        ):
            result = check_imports(("missing_module",), group_name="dependencies")

        self.assertFalse(result["passed"])
        self.assertIn("missing_module", result["detail"])
        self.assertIn("ModuleNotFoundError", result["detail"])

    def test_runtime_paths_remain_isolated(self):
        with TemporaryDirectory() as temp_dir:
            result = check_runtime_path_isolation(temp_dir)

        self.assertTrue(result["passed"])
        self.assertIn("paper=", result["detail"])
        self.assertIn("replay=", result["detail"])
        self.assertIn("live=", result["detail"])

    def test_write_access_probe_is_removed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "runtime-data"
            result = check_data_root_write_access(root)

            self.assertTrue(result["passed"])
            self.assertTrue(root.exists())
            self.assertFalse((root / ".hk50_write_probe").exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_aggregate_status_fails_when_a_check_fails(self):
        passing = {"name": "passing", "passed": True, "detail": "ok"}
        failing = {"name": "failing", "passed": False, "detail": "bad"}

        with TemporaryDirectory() as temp_dir, patch(
            "scripts.check_environment.check_python_version",
            return_value=failing,
        ), patch(
            "scripts.check_environment.check_imports",
            return_value=passing,
        ), patch(
            "scripts.check_environment.check_runtime_path_isolation",
            return_value=passing,
        ), patch(
            "scripts.check_environment.check_data_root_write_access",
            return_value=passing,
        ):
            report = run_environment_checks(temp_dir)

        self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
