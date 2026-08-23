from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.replay_context_matrix import analyze_context_matrix


if __name__ == "__main__":
    print(json.dumps(analyze_context_matrix(), indent=2, default=str))
