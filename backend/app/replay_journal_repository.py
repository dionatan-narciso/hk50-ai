"""Persistence boundary for the replay trade journal.

This module owns replay-journal filesystem operations so the historical replay
engine does not need to know where replay state is stored. Paths are resolved
at call time to support HK50_DATA_DIR overrides in tests and deployments.
"""

from pathlib import Path

import pandas as pd

from app.replay_context_instrumentation import build_replay_context_fields
from app.runtime_paths import resolve_runtime_paths


def get_replay_journal_path() -> Path:
    """Return the configured replay trade-journal path."""

    return resolve_runtime_paths().replay_trade_journal


def ensure_replay_journal_folder() -> Path:
    """Create the replay directory and return the journal path."""

    journal_path = get_replay_journal_path()
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    return journal_path


def reset_replay_journal() -> Path:
    """Remove the existing replay journal, if present."""

    journal_path = ensure_replay_journal_folder()
    if journal_path.exists():
        journal_path.unlink()
    return journal_path


def append_replay_trade(trade: dict) -> Path:
    """Append one trade plus informational Sprint 1B research fields.

    Context instrumentation runs only at persistence time, after replay has
    already decided, opened, and closed the trade. The derived fields therefore
    cannot alter historical trading behaviour.
    """

    journal_path = ensure_replay_journal_folder()
    enriched_trade = {
        **trade,
        **build_replay_context_fields(trade),
    }

    if journal_path.exists():
        journal = pd.read_csv(journal_path)
        journal = pd.concat(
            [journal, pd.DataFrame([enriched_trade])],
            ignore_index=True,
        )
    else:
        journal = pd.DataFrame([enriched_trade])

    journal.to_csv(journal_path, index=False)
    return journal_path
