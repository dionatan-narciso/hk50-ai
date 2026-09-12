from pathlib import Path
import json
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.dataset import build_and_freeze_default_oos_dataset  # noqa: E402
from app.runtime_paths import resolve_runtime_paths  # noqa: E402


if __name__ == "__main__":
    manifest = build_and_freeze_default_oos_dataset()
    paths = resolve_runtime_paths()

    print(
        json.dumps(
            {
                "status": "completed",
                "dataset_file": str(paths.validation_market_data),
                "manifest_file": str(paths.validation_dataset_manifest),
                "candidate_snapshot_sha256": manifest["candidate_snapshot_sha256"],
                "dataset_sha256": manifest["dataset_sha256"],
                "manifest_sha256": manifest["manifest_sha256"],
                "row_count": manifest["row_count"],
                "scored_row_count": manifest["scored_row_count"],
                "validation_window": manifest["validation_window"],
                "note": (
                    "OOS market data is frozen in the validation namespace. "
                    "No replay, paper, live, strategy, voting, entry or exit state was changed."
                ),
            },
            indent=2,
        )
    )
