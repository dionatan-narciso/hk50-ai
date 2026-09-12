from pathlib import Path
import json
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.dataset import (  # noqa: E402
    DEFAULT_EMBARGO_DAYS,
    DEFAULT_WARMUP_DAYS,
    build_default_validation_plan,
    candidate_snapshot_frozen_at,
    inspect_discovery_bounds,
)
from app.oos_validation.snapshot import load_candidate_snapshot  # noqa: E402


if __name__ == "__main__":
    bounds = inspect_discovery_bounds()
    snapshot = load_candidate_snapshot()
    frozen_at = candidate_snapshot_frozen_at()
    plan = build_default_validation_plan()

    print(
        json.dumps(
            {
                "status": "completed",
                "discovery_total_trades": bounds.total_trades,
                "candidate_count": snapshot["candidate_count"],
                "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
                "discovery_first_opened_at": bounds.first_opened_at.isoformat(),
                "discovery_last_closed_at": bounds.last_closed_at.isoformat(),
                "candidate_snapshot_frozen_at": frozen_at.isoformat(),
                "embargo_days": DEFAULT_EMBARGO_DAYS,
                "warmup_days": DEFAULT_WARMUP_DAYS,
                "validation_window": {
                    "start": plan.validation.start.isoformat(),
                    "end": plan.validation.end.isoformat(),
                },
                "note": (
                    "Inspection only. No market data was downloaded and no validation files were changed."
                ),
            },
            indent=2,
        )
    )
