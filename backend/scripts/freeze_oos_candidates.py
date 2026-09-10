from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.oos_validation.snapshot import freeze_candidate_snapshot, load_candidate_snapshot
from app.replay_context_candidates import build_context_candidate_report


if __name__ == "__main__":
    report = build_context_candidate_report()
    path = freeze_candidate_snapshot(report)
    snapshot = load_candidate_snapshot()
    print(json.dumps({
        "status": "completed",
        "snapshot_file": str(path),
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "candidate_count": snapshot["candidate_count"],
        "discovery_total_trades": snapshot["discovery_total_trades"],
        "note": "Candidate hypotheses are frozen for OOS validation.",
    }, indent=2))
