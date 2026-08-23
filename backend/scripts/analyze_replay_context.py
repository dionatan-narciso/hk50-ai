from __future__ import annotations

import json

from app.replay_context_analysis import analyze_replay_context


if __name__ == "__main__":
    print(json.dumps(analyze_replay_context(), indent=2, default=str))
