"""Canonical paper-trade journal access.

The repository accepts both the tracker closed-trade schema and the older
research journal schema. Rows are normalised to expose both naming conventions
so existing analytics and risk controls can share one configured file.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def get_paper_trade_journal_path() -> Path:
    return resolve_runtime_paths().paper_trade_journal


def _first_value(trade: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = trade.get(key)
        if value is not None:
            return value
    return default


def normalise_paper_trade(trade: Mapping[str, Any]) -> dict[str, Any]:
    """Return one row compatible with both existing journal schemas."""
    closed_at = _first_value(
        trade,
        "closed_at",
        "timestamp",
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    trade_return = float(_first_value(trade, "return_percent", "result_pct", default=0))
    strategy = _first_value(trade, "strategy", "reason", default="Unknown Strategy")
    direction = _first_value(trade, "direction", "signal", default="UNKNOWN")

    row = dict(trade)
    row.update({
        "timestamp": closed_at,
        "closed_at": closed_at,
        "strategy": strategy,
        "reason": _first_value(trade, "reason", "strategy", default=strategy),
        "direction": direction,
        "signal": _first_value(trade, "signal", "direction", default=direction),
        "result_pct": trade_return,
        "return_percent": trade_return,
    })
    return row


def append_paper_trade(trade: Mapping[str, Any]) -> dict[str, Any]:
    """Append one normalised trade to the configured paper journal."""
    journal_path = get_paper_trade_journal_path()
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    row = normalise_paper_trade(trade)
    new_row = pd.DataFrame([row])

    if journal_path.exists():
        existing = pd.read_csv(journal_path)
        all_columns = list(dict.fromkeys([*existing.columns, *new_row.columns]))
        existing = existing.reindex(columns=all_columns)
        new_row = new_row.reindex(columns=all_columns)
        combined = pd.concat([existing, new_row], ignore_index=True)
        combined.to_csv(journal_path, index=False)
    else:
        new_row.to_csv(journal_path, index=False)

    return row


def load_paper_trade_journal() -> pd.DataFrame:
    journal_path = get_paper_trade_journal_path()
    if not journal_path.exists():
        return pd.DataFrame()
    return pd.read_csv(journal_path)
