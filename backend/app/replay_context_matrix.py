from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd

from app.replay_context_analysis import CATEGORICAL_CONTEXT_COLUMNS
from app.replay_journal_repository import get_replay_journal_path


DEFAULT_MIN_TRADES = 8
DEFAULT_MAX_DIMENSIONS = 2


def _clean_value(value: Any) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    text = str(value).strip()
    return text if text else "UNKNOWN"


def _combination_stats(group: pd.DataFrame, dimensions: tuple[str, ...]) -> dict[str, Any] | None:
    returns = pd.to_numeric(group["return_percent"], errors="coerce").dropna()
    if returns.empty:
        return None

    wins = int((returns > 0).sum())
    losses = int((returns <= 0).sum())
    total = int(len(returns))
    gross_profit = float(returns[returns > 0].sum())
    gross_loss = abs(float(returns[returns <= 0].sum()))

    return {
        "dimensions": list(dimensions),
        "context": {
            dimension: _clean_value(group.iloc[0][dimension])
            for dimension in dimensions
        },
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 2),
        "average_return": round(float(returns.mean()), 3),
        "median_return": round(float(returns.median()), 3),
        "total_return": round(float(returns.sum()), 3),
        "profit_factor": (
            round(gross_profit / gross_loss, 3)
            if gross_loss > 0
            else None
        ),
    }


def analyze_context_matrix(
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    max_dimensions: int = DEFAULT_MAX_DIMENSIONS,
) -> dict[str, Any]:
    """Rank replay context combinations without feeding results into trading logic."""
    if min_trades < 1:
        raise ValueError("min_trades must be at least 1")
    if max_dimensions < 1:
        raise ValueError("max_dimensions must be at least 1")

    journal_path = get_replay_journal_path()
    if not journal_path.exists():
        return {"status": "no_data", "total_trades": 0, "rows": []}

    df = pd.read_csv(journal_path)
    if df.empty or "return_percent" not in df.columns:
        return {"status": "no_data", "total_trades": 0, "rows": []}

    dimensions = [
        column
        for column in CATEGORICAL_CONTEXT_COLUMNS
        if column in df.columns
    ]

    rows: list[dict[str, Any]] = []
    upper = min(max_dimensions, len(dimensions))
    for size in range(1, upper + 1):
        for selected in combinations(dimensions, size):
            working = df.copy()
            for column in selected:
                working[column] = working[column].map(_clean_value)

            grouper: Any = selected[0] if len(selected) == 1 else list(selected)
            for _, group in working.groupby(grouper, sort=False, dropna=False):
                if len(group) < min_trades:
                    continue
                stats = _combination_stats(group, selected)
                if stats is not None:
                    rows.append(stats)

    rows.sort(
        key=lambda row: (
            -row["average_return"],
            -row["trades"],
            tuple(row["context"].values()),
        )
    )

    positive = [row for row in rows if row["average_return"] > 0]
    negative = sorted(
        (row for row in rows if row["average_return"] < 0),
        key=lambda row: (row["average_return"], -row["trades"]),
    )

    return {
        "status": "completed",
        "total_trades": int(len(df)),
        "min_trades": min_trades,
        "max_dimensions": max_dimensions,
        "eligible_dimensions": dimensions,
        "rows": rows,
        "best_positive": positive[:10],
        "worst_negative": negative[:10],
        "note": (
            "Research matrix is observational only. Rows below the minimum sample "
            "size are excluded and no result is applied to trading logic."
        ),
    }
