from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.forward_batches import build_batch_manifest, register_batch
from app.runtime_paths import resolve_runtime_paths


def main() -> None:
    paths = resolve_runtime_paths()
    dataset_manifest = json.loads(paths.validation_dataset_manifest.read_text(encoding="utf-8"))
    result = json.loads(paths.validation_result_report.read_text(encoding="utf-8"))
    window = dataset_manifest["validation_window"]
    manifest = build_batch_manifest(
        batch_id="batch-001",
        candidate_snapshot_sha256=dataset_manifest["candidate_snapshot_sha256"],
        dataset_sha256=dataset_manifest["dataset_sha256"],
        validation_start=pd.Timestamp(window["start"]).to_pydatetime(),
        validation_end=pd.Timestamp(window["end"]).to_pydatetime(),
        scored_row_count=dataset_manifest["scored_row_count"],
        trade_count=result["baseline"]["trades"],
    )
    registry = register_batch(manifest)
    print(json.dumps({
        "status": "completed",
        "registered_batch": manifest,
        "batch_count": len(registry["batches"]),
        "registry_file": str(paths.validation_dir / "forward_batches" / "registry.json"),
        "note": "OOS Batch 1 is registered as immutable forward-validation evidence.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
