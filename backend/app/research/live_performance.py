"""Pure live-performance ranking used by the Research Director.

This module reproduces the legacy Research Director's ordering and score
thresholds without reading or writing runtime state. Keeping it pure makes the
behaviour easy to characterize before production wiring is changed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


SORT_FIELDS = ("win_rate", "average_return", "total_trades")


def calculate_live_score(best_strategy: Mapping[str, Any] | None) -> int:
    """Return the legacy Research Director live score for one strategy."""
    if not best_strategy:
        return 0

    win_rate = float(best_strategy.get("win_rate", 0))
    average_return = float(best_strategy.get("average_return", 0))
    total_trades = int(best_strategy.get("total_trades", 0))

    if total_trades >= 10 and win_rate >= 60 and average_return > 0:
        return 25
    if total_trades >= 5 and win_rate >= 55 and average_return > 0:
        return 18
    if total_trades >= 3 and average_return > 0:
        return 12
    if total_trades >= 1 and average_return > 0:
        return 5
    return 0


def rank_live_performance(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the legacy live-performance context from in-memory records.

    Ordering matches the previous pandas sort: win rate, average return, then
    total trades, all descending. Input records are copied so callers retain
    ownership of their data.
    """
    live_performance = [dict(record) for record in records]

    if not live_performance:
        return {
            "live_performance": [],
            "best_live_strategy": None,
            "live_score": 0,
        }

    ranked = sorted(
        live_performance,
        key=lambda row: (
            float(row.get("win_rate", 0)),
            float(row.get("average_return", 0)),
            int(row.get("total_trades", 0)),
        ),
        reverse=True,
    )

    best_live_strategy = ranked[0]

    return {
        # Preserve the old API behaviour: the full list reflects file order,
        # while best_live_strategy is selected from a sorted view.
        "live_performance": live_performance,
        "best_live_strategy": best_live_strategy,
        "live_score": calculate_live_score(best_live_strategy),
    }
