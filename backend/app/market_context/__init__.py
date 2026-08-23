"""Market-context construction helpers for live, replay, and future data sources."""

from app.market_context.conditions import (
    MarketConditionContext,
    calculate_ma_separation_percent,
    classify_trend_strength,
    classify_volatility,
    derive_market_condition_context,
)
from app.market_context.pipeline import build_enriched_market_context
from app.market_context.sessions import (
    TradingSessionContext,
    derive_trading_session_context,
)
from app.market_context.structure import (
    MarketStructureContext,
    calculate_signed_distance_percent,
    classify_directional_structure,
    classify_ma_alignment,
    classify_price_position,
    derive_market_structure_context,
)
from app.market_context.timeframes import TimeframeSnapshot, build_market_context
from app.market_context.trends import (
    HigherTimeframeTrendContext,
    derive_higher_timeframe_trend_context,
    normalize_trend,
)

__all__ = [
    "HigherTimeframeTrendContext",
    "MarketConditionContext",
    "MarketStructureContext",
    "TimeframeSnapshot",
    "TradingSessionContext",
    "build_enriched_market_context",
    "build_market_context",
    "calculate_ma_separation_percent",
    "calculate_signed_distance_percent",
    "classify_directional_structure",
    "classify_ma_alignment",
    "classify_price_position",
    "classify_trend_strength",
    "classify_volatility",
    "derive_higher_timeframe_trend_context",
    "derive_market_condition_context",
    "derive_market_structure_context",
    "derive_trading_session_context",
    "normalize_trend",
]
