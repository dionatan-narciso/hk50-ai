from __future__ import annotations

from typing import Any

import pandas as pd

from app.replay_context_matrix import (
    DEFAULT_MAX_DIMENSIONS,
    DEFAULT_MIN_TRADES,
    analyze_context_matrix,
)
from app.replay_journal_repository import get_replay_journal_path


DEFAULT_FOLDS = 3


def _matches_context(df: pd.DataFrame, context: dict[str, str]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for column, expected in context.items():
        if column not in df.columns:
            return pd.Series(False, index=df.index)
        values = df[column].fillna("UNKNOWN").astype(str).str.strip().replace("", "UNKNOWN")
        mask &= values.eq(expected)
    return mask


def _fold_stats(df: pd.DataFrame, context: dict[str, str], folds: int) -> list[dict[str, Any]]:
    matched = df[_matches_context(df, context)].copy()
    if matched.empty:
        return []

    if "opened_at" in matched.columns:
        opened = pd.to_datetime(matched["opened_at"], errors="coerce", utc=True)
        matched = matched.assign(_opened=opened).sort_values("_opened", kind="stable")

    partitions = [part for part in __import__("numpy").array_split(matched, folds) if not part.empty]
    rows: list[dict[str, Any]] = []
    for index, part in enumerate(partitions, start=1):
        returns = pd.to_numeric(part["return_percent"], errors="coerce").dropna()
        if returns.empty:
            continue
        wins = int((returns > 0).sum())
        rows.append({
            "fold": index,
            "trades": int(len(returns)),
            "win_rate": round(wins / len(returns) * 100, 2),
            "average_return": round(float(returns.mean()), 3),
        })
    return rows


def analyze_context_robustness(
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    max_dimensions: int = DEFAULT_MAX_DIMENSIONS,
    folds: int = DEFAULT_FOLDS,
) -> dict[str, Any]:
    """Check whether context expectancy persists across chronological trade folds."""
    if folds < 2:
        raise ValueError("folds must be at least 2")

    matrix = analyze_context_matrix(
        min_trades=min_trades,
        max_dimensions=max_dimensions,
    )
    if matrix["status"] != "completed":
        return {"status": "no_data", "total_trades": 0, "rows": []}

    journal_path = get_replay_journal_path()
    df = pd.read_csv(journal_path)
    rows: list[dict[str, Any]] = []

    for candidate in matrix["rows"]:
        fold_rows = _fold_stats(df, candidate["context"], folds)
        if not fold_rows:
            continue

        positive_folds = sum(row["average_return"] > 0 for row in fold_rows)
        negative_folds = sum(row["average_return"] < 0 for row in fold_rows)
        overall_sign = 1 if candidate["average_return"] > 0 else -1 if candidate["average_return"] < 0 else 0
        same_sign_folds = sum(
            (row["average_return"] > 0 and overall_sign > 0)
            or (row["average_return"] < 0 and overall_sign < 0)
            or (row["average_return"] == 0 and overall_sign == 0)
            for row in fold_rows
        )

        rows.append({
            **candidate,
            "folds": fold_rows,
            "positive_folds": positive_folds,
            "negative_folds": negative_folds,
            "same_sign_folds": same_sign_folds,
            "fold_consistency_percent": round(same_sign_folds / len(fold_rows) * 100, 2),
            "robust": len(fold_rows) == folds and same_sign_folds == folds,
        })

    rows.sort(
        key=lambda row: (
            -row["fold_consistency_percent"],
            -abs(row["average_return"]),
            -row["trades"],
        )
    )

    return {
        "status": "completed",
        "total_trades": matrix["total_trades"],
        "min_trades": min_trades,
        "max_dimensions": max_dimensions,
        "fold_count": folds,
        "rows": rows,
        "robust_positive": [
            row for row in rows if row["robust"] and row["average_return"] > 0
        ][:10],
        "robust_negative": [
            row for row in rows if row["robust"] and row["average_return"] < 0
        ][:10],
        "note": (
            "Robustness is observational only. A row is marked robust only when its "
            "expectancy sign is consistent across every chronological fold."
        ),
    }
