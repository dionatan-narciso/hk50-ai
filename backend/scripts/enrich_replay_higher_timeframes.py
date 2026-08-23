from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.historical_replay_engine import load_hk50_history
from app.replay_higher_timeframe_enrichment import (
    enrich_replay_journal_with_higher_timeframes,
)


if __name__ == "__main__":
    history = load_hk50_history(period="1y", interval="1h")
    result = enrich_replay_journal_with_higher_timeframes(history)
    print(json.dumps(result, indent=2, default=str))
