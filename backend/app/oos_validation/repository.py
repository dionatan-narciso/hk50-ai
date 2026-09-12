from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.replay_context_instrumentation import build_replay_context_fields
from app.runtime_paths import resolve_runtime_paths


def get_validation_journal_path(path: Path | None = None) -> Path:
    return path or resolve_runtime_paths().validation_trade_journal


def reset_validation_journal(path: Path | None = None) -> Path:
    target = get_validation_journal_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    return target


def append_validation_trade(trade: dict, path: Path | None = None) -> Path:
    """Append one OOS trade plus informational context in validation storage only."""
    target = get_validation_journal_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    enriched = {
        **trade,
        **build_replay_context_fields(trade),
    }
    row = pd.DataFrame([enriched])
    if target.exists():
        existing = pd.read_csv(target)
        row = pd.concat([existing, row], ignore_index=True)
    row.to_csv(target, index=False)
    return target
