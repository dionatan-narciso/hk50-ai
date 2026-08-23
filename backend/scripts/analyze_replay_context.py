from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.replay_context_analysis import analyze_replay_context


if __name__ == "__main__":
    print(json.dumps(analyze_replay_context(), indent=2, default=str))
