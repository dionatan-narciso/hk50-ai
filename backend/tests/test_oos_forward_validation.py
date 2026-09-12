import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from app.oos_validation.evidence import classify_evidence
from app.oos_validation.forward_batches import build_batch_manifest, register_batch


class ForwardOosValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.env = patch.dict(os.environ, {"HK50_DATA_DIR": self.temp_dir.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_evidence_ladder(self):
        self.assertEqual(classify_evidence(4).label, "INSUFFICIENT")
        self.assertEqual(classify_evidence(5).label, "PRELIMINARY")
        self.assertEqual(classify_evidence(10).label, "DEVELOPING")
        self.assertEqual(classify_evidence(20).label, "MEANINGFUL")
        self.assertEqual(classify_evidence(30).label, "STRONGER_EVIDENCE")

    def test_negative_trade_count_rejected(self):
        with self.assertRaises(ValueError):
            classify_evidence(-1)

    def test_batch_registration_is_idempotent(self):
        manifest = self._manifest("batch-001", 1, 2)
        first = register_batch(manifest)
        second = register_batch(manifest)
        self.assertEqual(len(first["batches"]), 1)
        self.assertEqual(first, second)

    def test_batch_mutation_is_rejected(self):
        register_batch(self._manifest("batch-001", 1, 2))
        changed = self._manifest("batch-001", 1, 3)
        with self.assertRaises(RuntimeError):
            register_batch(changed)

    def test_overlapping_batches_are_rejected(self):
        register_batch(self._manifest("batch-001", 1, 3))
        with self.assertRaises(RuntimeError):
            register_batch(self._manifest("batch-002", 2, 4))

    def test_adjacent_batches_are_allowed(self):
        register_batch(self._manifest("batch-001", 1, 2))
        registry = register_batch(self._manifest("batch-002", 2, 3))
        self.assertEqual(len(registry["batches"]), 2)

    def _manifest(self, batch_id, start_day, end_day):
        return build_batch_manifest(
            batch_id=batch_id,
            candidate_snapshot_sha256="a" * 64,
            dataset_sha256=(batch_id[-1] or "1") * 64,
            validation_start=datetime(2026, 9, start_day, tzinfo=timezone.utc),
            validation_end=datetime(2026, 9, end_day, tzinfo=timezone.utc),
            scored_row_count=10,
            trade_count=2,
        )


if __name__ == "__main__":
    unittest.main()
