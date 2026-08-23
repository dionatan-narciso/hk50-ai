from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Mapping

from app.market_context.conditions import derive_market_condition_context
from app.market_context.sessions import derive_trading_session_context
from app.market_context.structure import derive_market_structure_context
from app.market_context.timeframes import TimeframeSnapshot, build_market_context
from app.market_context.trends import derive_higher_timeframe_trend_context
from app.strategies.contracts import MarketContext


def build_enriched_market_context(
    primary: TimeframeSnapshot,
    *higher_timeframes: TimeframeSnapshot,
    timestamp: datetime,
    metadata: Mapping[str, Any] | None = None,
    regime: Mapping[str, Any] | None = None,
) -> MarketContext:
    """Build one standardized informational market context.

    Sprint 1B.7 centralizes enrichment construction without changing trading
    behavior. Existing strategies continue to read only ``context.data``.
    Enriched values remain isolated in ``session``, ``structure``, and
    ``features`` namespaces until a later, explicitly tested consumer opts in.
    """
    base_context = build_market_context(
        primary,
        *higher_timeframes,
        metadata=metadata,
        regime=regime,
    )

    higher_trend = derive_higher_timeframe_trend_context(base_context)
    session = derive_trading_session_context(timestamp)
    condition = derive_market_condition_context(primary.data)
    structure = derive_market_structure_context(primary.data)

    features = {
        "higher_timeframe_trend": asdict(higher_trend),
        "market_condition": asdict(condition),
    }

    return build_market_context(
        primary,
        *higher_timeframes,
        metadata=metadata,
        regime=regime,
        session=asdict(session),
        structure=asdict(structure),
        features=features,
    )
