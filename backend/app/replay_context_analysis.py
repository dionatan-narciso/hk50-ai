from __future__ import annotations

from typing import Any

import pandas as pd

from app.replay_journal_repository import get_replay_journal_path


CATEGORICAL_CONTEXT_COLUMNS = (
    "context_session",
    "context_volatility",
    "context_trend_strength",
    "context_directional_structure",
    "context_price_position",
    "context_ma_alignment",
    "context_nearest_anchor",
)

NUMERIC_CONTEXT_COLUMNS = (
    "context_ma_separation_percent",
    "context_distance_ma20_percent",
    "context_distance_ma50_percent",
    "context_nearest_anchor_distance_percent",
)


def _category_stats(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for value, group in df.groupby(column, dropna=False, sort=False):
        returns = pd.to_numeric(group["return_percent"], errors="coerce").dropna()
        if returns.empty:
            continue
        wins = int((returns > 0).sum())
        total = int(len(returns))
        rows.append(
            {
                "value": "UNKNOWN" if pd.isna(value) else str(value),
                "trades": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": round(wins / total * 100, 2),
                "average_return": round(float(returns.mean()), 3),
            }
        )

    return rows


def _numeric_stats(df: pd.DataFrame, column: str) -> dict[str, Any]:
    values = pd.to_numeric(df[column], errors="coerce")
    returns = pd.to_numeric(df["return_percent"], errors="coerce")
    valid = values.notna() & returns.notna()
    values = values[valid]
    returns = returns[valid]

    if values.empty:
        return {
            "observations": 0,
            "winner_average": None,
            "loser_average": None,
            "overall_average": None,
        }

    winner_values = values[returns > 0]
    loser_values = values[returns <= 0]

    return {
        "observations": int(len(values)),
        "winner_average": (
            round(float(winner_values.mean()), 4)
            if not winner_values.empty
            else None
        ),
        "loser_average": (
            round(float(loser_values.mean()), 4)
            if not loser_values.empty
            else None
        ),
        "overall_average": round(float(values.mean()), 4),
    }


def analyze_replay_context() -> dict[str, Any]:
    """Summarize replay outcomes by informational Sprint 1B context fields."""
    journal_path = get_replay_journal_path()
    if not journal_path.exists():
        return {
            "status": "no_data",
            "total_trades": 0,
            "categorical": {},
            "numeric": {},
        }

    df = pd.read_csv(journal_path)
    if df.empty or "return_percent" not in df.columns:
        return {
            "status": "no_data",
            "total_trades": 0,
            "categorical": {},
            "numeric": {},
        }

    categorical = {
        column: _category_stats(df, column)
        for column in CATEGORICAL_CONTEXT_COLUMNS
        if column in df.columns
    }
    numeric = {
        column: _numeric_stats(df, column)
        for column in NUMERIC_CONTEXT_COLUMNS
        if column in df.columns
    }

    return {
        "status": "completed",
        "total_trades": int(len(df)),
        "categorical": categorical,
        "numeric": numeric,
        "note": (
            "Context analysis is observational only. No result is applied to "
            "strategy, confidence, risk, or learning logic."
        ),
    }
