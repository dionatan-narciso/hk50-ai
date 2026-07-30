import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.runtime_paths import (
    BACKEND_ROOT,
    DATA_ROOT_ENV_VAR,
    DEFAULT_DATA_ROOT,
    resolve_runtime_paths,
)


class RuntimePathsTests(unittest.TestCase):
    def test_default_data_root_is_backend_data(self):
        with patch.dict(os.environ, {}, clear=True):
            paths = resolve_runtime_paths()

        self.assertEqual(DEFAULT_DATA_ROOT, BACKEND_ROOT / "data")
        self.assertEqual(paths.data_root, DEFAULT_DATA_ROOT.resolve())

    def test_explicit_root_is_split_by_execution_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = resolve_runtime_paths(temp_dir)
            root = Path(temp_dir).resolve()

            self.assertEqual(paths.paper_dir, root / "paper")
            self.assertEqual(paths.replay_dir, root / "replay")
            self.assertEqual(paths.live_dir, root / "live")
            self.assertNotEqual(paths.paper_dir, paths.replay_dir)
            self.assertNotEqual(paths.paper_dir, paths.live_dir)
            self.assertNotEqual(paths.replay_dir, paths.live_dir)

    def test_replay_files_cannot_resolve_inside_paper_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = resolve_runtime_paths(temp_dir)

            replay_files = (
                paths.replay_trade_journal,
                paths.replay_learning_memory,
                paths.replay_learning_control,
                paths.replay_entry_learning_memory,
                paths.replay_entry_weight_tuning_log,
            )

            for replay_file in replay_files:
                self.assertEqual(replay_file.parent, paths.replay_dir)
                self.assertNotEqual(replay_file.parent, paths.paper_dir)

    def test_environment_override_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {DATA_ROOT_ENV_VAR: temp_dir}, clear=True):
                paths = resolve_runtime_paths()

            self.assertEqual(paths.data_root, Path(temp_dir).resolve())

    def test_explicit_root_takes_precedence_over_environment(self):
        with tempfile.TemporaryDirectory() as env_dir:
            with tempfile.TemporaryDirectory() as explicit_dir:
                with patch.dict(
                    os.environ,
                    {DATA_ROOT_ENV_VAR: env_dir},
                    clear=True,
                ):
                    paths = resolve_runtime_paths(explicit_dir)

                self.assertEqual(paths.data_root, Path(explicit_dir).resolve())

    def test_resolving_paths_has_no_filesystem_side_effects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "not-created"
            paths = resolve_runtime_paths(root)

            self.assertEqual(paths.data_root, root.resolve())
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
