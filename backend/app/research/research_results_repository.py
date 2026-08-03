"""Persistence boundary for saved research-lab results.

Research results are paper/research state. This module centralises their
filesystem path and preserves the existing append/read CSV behaviour.
"""

from pathlib import Path

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


COLUMNS = [
    "timestamp",
    "lab_type",
    "rank",
    "strategy",
    "trades",
    "win_rate",
    "profit_factor",
    "total_return",
    "average_trade",
    "max_drawdown",
    "signal",
]


def get_research_results_path() -> Path:
    return resolve_runtime_paths().paper_research_results


def append_research_results(rows: list[dict]) -> Path:
    path = get_research_results_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame(rows, columns=COLUMNS)
    if path.exists():
        frame.to_csv(path, mode="a", header=False, index=False)
    else:
        frame.to_csv(path, index=False)

    return path


def load_research_results() -> pd.DataFrame:
    path = get_research_results_path()
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path)
