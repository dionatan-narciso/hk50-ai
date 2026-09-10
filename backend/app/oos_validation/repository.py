from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def get_validation_journal_path() -> Path:
    return resolve_runtime_paths().validation_trade_journal


def reset_validation_journal() -> Path:
    path = get_validation_journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return path


def append_validation_trade(trade: dict) -> Path:
    """Append one OOS validation trade without touching replay or paper state."""
    path = get_validation_journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([dict(trade)])
    if path.exists():
        existing = pd.read_csv(path)
        row = pd.concat([existing, row], ignore_index=True)
    row.to_csv(path, index=False)
    return path
