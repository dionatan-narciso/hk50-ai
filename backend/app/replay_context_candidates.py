from __future__ import annotations

from typing import Any

import pandas as pd

from app.replay_context_robustness import (
    DEFAULT_FOLDS,
    _matches_context,
    analyze_context_robustness,
)
from app.replay_journal_repository import get_replay_journal_path


PROMISING_MIN_TRADES = 12
PROMISING_MIN_ABS_RETURN = 0.15
WATCH_MIN_TRADES = 8


def _membership_signature(df: pd.DataFrame, context: dict[str, str]) -> tuple[int, ...]:
    mask = _matches_context(df, context)
    return tuple(int(index) for index in df.index[mask])


def _representative_rank(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        len(row["dimensions"]),
        -row["trades"],
        tuple(row["dimensions"]),
        tuple(row["context"].values()),
    )


def _classification(row: dict[str, Any]) -> str:
    if not row["robust"]:
        return "REJECT"
    if row["trades"] < WATCH_MIN_TRADES:
        return "INSUFFICIENT_SAMPLE"
    if (
        row["trades"] >= PROMISING_MIN_TRADES
        and abs(row["average_return"]) >= PROMISING_MIN_ABS_RETURN
    ):
        return "PROMISING"
    return "WATCH"


def build_context_candidate_report(
    *,
    min_trades: int = WATCH_MIN_TRADES,
    max_dimensions: int = 2,
    folds: int = DEFAULT_FOLDS,
) -> dict[str, Any]:
    """Collapse equivalent replay patterns into distinct evidence candidates."""
    robustness = analyze_context_robustness(
        min_trades=min_trades,
        max_dimensions=max_dimensions,
        folds=folds,
    )
    if robustness["status"] != "completed":
        return {"status": "no_data", "total_trades": 0, "candidates": []}

    journal_path = get_replay_journal_path()
    df = pd.read_csv(journal_path)

    groups: dict[tuple[int, ...], list[dict[str, Any]]] = {}
    for row in robustness["rows"]:
        signature = _membership_signature(df, row["context"])
        if not signature:
            continue
        groups.setdefault(signature, []).append(row)

    candidates: list[dict[str, Any]] = []
    for signature, equivalent_rows in groups.items():
        representative = min(equivalent_rows, key=_representative_rank)
        classification = _classification(representative)

        candidates.append({
            "classification": classification,
            "direction": (
                "POSITIVE"
                if representative["average_return"] > 0
                else "NEGATIVE"
                if representative["average_return"] < 0
                else "NEUTRAL"
            ),
            "representative": {
                "dimensions": representative["dimensions"],
                "context": representative["context"],
            },
            "equivalent_patterns": [
                {
                    "dimensions": row["dimensions"],
                    "context": row["context"],
                }
                for row in sorted(equivalent_rows, key=_representative_rank)
            ],
            "equivalent_pattern_count": len(equivalent_rows),
            "trades": representative["trades"],
            "wins": representative["wins"],
            "losses": representative["losses"],
            "win_rate": representative["win_rate"],
            "average_return": representative["average_return"],
            "median_return": representative["median_return"],
            "total_return": representative["total_return"],
            "profit_factor": representative["profit_factor"],
            "fold_consistency_percent": representative["fold_consistency_percent"],
            "robust": representative["robust"],
            "folds": representative["folds"],
            "matched_trade_count": len(signature),
        })

    classification_order = {
        "PROMISING": 0,
        "WATCH": 1,
        "INSUFFICIENT_SAMPLE": 2,
        "REJECT": 3,
    }
    candidates.sort(
        key=lambda row: (
            classification_order[row["classification"]],
            -abs(row["average_return"]),
            -row["trades"],
        )
    )

    counts = {
        name: sum(candidate["classification"] == name for candidate in candidates)
        for name in classification_order
    }

    return {
        "status": "completed",
        "total_trades": robustness["total_trades"],
        "raw_pattern_count": len(robustness["rows"]),
        "distinct_candidate_count": len(candidates),
        "deduplicated_pattern_count": len(robustness["rows"]) - len(candidates),
        "classification_counts": counts,
        "candidates": candidates,
        "promising": [
            candidate
            for candidate in candidates
            if candidate["classification"] == "PROMISING"
        ],
        "watch": [
            candidate
            for candidate in candidates
            if candidate["classification"] == "WATCH"
        ],
        "note": (
            "Candidates are deduplicated by exact matched replay-trade membership. "
            "Classifications are research labels only and do not alter trading logic."
        ),
    }
