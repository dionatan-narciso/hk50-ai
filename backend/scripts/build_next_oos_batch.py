from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.forward_dataset import build_next_batch_dataset


def main() -> None:
    manifest = build_next_batch_dataset()
    print(json.dumps({
        "status": "completed",
        "batch_id": manifest["batch_id"],
        "candidate_snapshot_sha256": manifest["candidate_snapshot_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "row_count": manifest["row_count"],
        "scored_row_count": manifest["scored_row_count"],
        "execution_start": manifest["execution_start"],
        "validation_window": manifest["validation_window"],
        "note": "Forward OOS batch dataset frozen. Trading evaluation is a separate step.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
