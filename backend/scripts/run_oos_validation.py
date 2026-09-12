from __future__ import annotations

import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.evaluation import evaluate_frozen_candidates


def main() -> None:
    report = evaluate_frozen_candidates(run_replay=True)
    summary = {
        "status": report["status"],
        "candidate_count": report["candidate_count"],
        "minimum_oos_trades": report["minimum_oos_trades"],
        "baseline": report["baseline"],
        "status_counts": report["status_counts"],
        "replay_summary": report["replay_summary"],
        "result_file": str(
            BACKEND_ROOT / "data" / "validation" / "validation_result_report.json"
        ),
        "note": report["note"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
