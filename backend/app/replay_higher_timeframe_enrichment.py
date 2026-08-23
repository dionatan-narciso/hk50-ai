from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.replay_higher_timeframe_context import derive_replay_higher_timeframe_context
from app.replay_journal_repository import get_replay_journal_path


HTF_COLUMNS = (
    "context_htf_trend_4h",
    "context_htf_trend_1d",
    "context_htf_agreement",
    "context_htf_aligned_direction",
)


def enrich_replay_journal_with_higher_timeframes(
    history: pd.DataFrame,
    journal_path: Path | None = None,
) -> dict[str, Any]:
    """Add leak-free 4H/Daily context to an existing replay journal.

    This is deliberately post-replay instrumentation. It cannot change which
    trades opened or closed because the replay has already completed.
    """
    path = journal_path or get_replay_journal_path()
    if not path.exists():
        return {"status": "no_data", "trades_enriched": 0, "output_file": str(path)}

    journal = pd.read_csv(path)
    if journal.empty or "opened_at" not in journal.columns:
        return {"status": "no_data", "trades_enriched": 0, "output_file": str(path)}

    trends_4h: list[str] = []
    trends_1d: list[str] = []
    agreements: list[str] = []
    aligned_directions: list[str | None] = []

    for opened_at in journal["opened_at"]:
        context = derive_replay_higher_timeframe_context(history, opened_at)
        trends_4h.append(context.trend_4h)
        trends_1d.append(context.trend_1d)
        agreements.append(context.agreement)
        aligned_directions.append(context.aligned_direction)

    journal["context_htf_trend_4h"] = trends_4h
    journal["context_htf_trend_1d"] = trends_1d
    journal["context_htf_agreement"] = agreements
    journal["context_htf_aligned_direction"] = aligned_directions
    journal.to_csv(path, index=False)

    return {
        "status": "completed",
        "trades_enriched": int(len(journal)),
        "output_file": str(path),
        "columns": list(HTF_COLUMNS),
        "note": "Higher-timeframe replay context is observational only and was added after replay completion.",
    }
