from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.forward_batches import _load_registry
from app.oos_validation.forward_dataset import next_batch_id
from app.oos_validation.forward_evaluation import evaluate_and_register_forward_batch


def main() -> None:
    batch_id = next_batch_id(_load_registry())
    report = evaluate_and_register_forward_batch(batch_id)
    print(json.dumps({
        "status": report["status"],
        "batch_id": report["batch_id"],
        "batch_baseline": report["batch"]["baseline"],
        "cumulative_baseline": report["cumulative"]["baseline"],
        "cumulative_status_counts": report["cumulative"]["status_counts"],
        "cumulative_evidence_counts": report["cumulative"]["evidence_counts"],
        "registered_batch_count": report["registered_batch_count"],
        "note": report["note"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
