from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.market_context.conditions import derive_market_condition_context
from app.market_context.sessions import derive_trading_session_context
from app.market_context.structure import derive_market_structure_context


def _parse_entry_timestamp(value: Any) -> datetime | None:
    """Parse a replay entry timestamp without inventing a timezone.

    Historical replay timestamps are expected to be timezone-aware. If a legacy
    journal row is naive or malformed, instrumentation skips session labeling
    rather than guessing and contaminating research data.
    """
    if isinstance(value, datetime):
        timestamp = value
    else:
        try:
            timestamp = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return None
    return timestamp


def build_replay_context_fields(trade: Mapping[str, Any]) -> dict[str, Any]:
    """Derive informational Sprint 1B fields from a completed replay trade.

    The function reads only entry-time values already persisted by replay. It
    cannot affect the historical decision because it runs after the trade has
    closed, immediately before journal persistence.
    """
    snapshot = {
        "price": trade.get("close_at_entry", trade.get("entry_price")),
        "ma20": trade.get("ma20_at_entry"),
        "ma50": trade.get("ma50_at_entry"),
        "atr_percent": trade.get("atr_percent_at_entry"),
        "trend": trade.get("trend_at_entry", "Unknown"),
    }

    condition = derive_market_condition_context(snapshot)
    structure = derive_market_structure_context(snapshot)

    fields: dict[str, Any] = {
        "context_volatility": condition.volatility,
        "context_trend_strength": condition.trend_strength,
        "context_ma_separation_percent": condition.ma_separation_percent,
        "context_directional_structure": structure.directional_structure,
        "context_price_position": structure.price_position,
        "context_ma_alignment": structure.ma_alignment,
        "context_distance_ma20_percent": structure.distance_to_ma20_percent,
        "context_distance_ma50_percent": structure.distance_to_ma50_percent,
        "context_nearest_anchor": structure.nearest_anchor,
        "context_nearest_anchor_distance_percent": (
            structure.nearest_anchor_distance_percent
        ),
    }

    timestamp = _parse_entry_timestamp(trade.get("opened_at"))
    if timestamp is None:
        fields.update(
            {
                "context_session": "UNKNOWN",
                "context_session_overlap": False,
                "context_session_quiet": False,
            }
        )
    else:
        session = derive_trading_session_context(timestamp)
        fields.update(
            {
                "context_session": session.label,
                "context_session_overlap": session.is_overlap,
                "context_session_quiet": session.is_quiet,
            }
        )

    return fields
