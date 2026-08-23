"""Market-context construction helpers for live, replay, and future data sources."""

from app.market_context.conditions import (
    MarketConditionContext,
    calculate_ma_separation_percent,
    classify_trend_strength,
    classify_volatility,
    derive_market_condition_context,
)
from app.market_context.sessions import (
    TradingSessionContext,
    derive_trading_session_context,
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
    "TimeframeSnapshot",
    "TradingSessionContext",
    "build_market_context",
    "calculate_ma_separation_percent",
    "classify_trend_strength",
    "classify_volatility",
    "derive_higher_timeframe_trend_context",
    "derive_market_condition_context",
    "derive_trading_session_context",
    "normalize_trend",
]
