from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.strategies.contracts import MarketContext


VALID_TRENDS = frozenset({"Bullish", "Bearish", "Neutral"})


@dataclass(frozen=True)
class HigherTimeframeTrendContext:
    """Informational summary of trend direction across higher timeframes."""

    trends: Mapping[str, str]
    agreement: str
    aligned_direction: str | None
    bullish_count: int
    bearish_count: int
    neutral_count: int


def normalize_trend(value: object) -> str:
    """Normalize existing trend labels without inferring a direction."""
    text = str(value or "").strip().lower()
    if text == "bullish":
        return "Bullish"
    if text == "bearish":
        return "Bearish"
    return "Neutral"


def derive_higher_timeframe_trend_context(
    context: MarketContext,
) -> HigherTimeframeTrendContext:
    """Summarize higher-timeframe trends without changing strategy behavior.

    The result is informational only. Existing strategies continue to read the
    primary ``context.data`` mapping and do not consume this summary yet.
    """
    trends = {
        timeframe: normalize_trend(snapshot.get("trend"))
        for timeframe, snapshot in context.higher_timeframes.items()
    }

    bullish_count = sum(trend == "Bullish" for trend in trends.values())
    bearish_count = sum(trend == "Bearish" for trend in trends.values())
    neutral_count = sum(trend == "Neutral" for trend in trends.values())
    directional_count = bullish_count + bearish_count

    if not trends:
        agreement = "NO_HIGHER_TIMEFRAMES"
        aligned_direction = None
    elif directional_count == 0:
        agreement = "NEUTRAL"
        aligned_direction = None
    elif bullish_count and bearish_count:
        agreement = "CONFLICTING"
        aligned_direction = None
    elif bullish_count:
        agreement = "ALIGNED"
        aligned_direction = "Bullish"
    else:
        agreement = "ALIGNED"
        aligned_direction = "Bearish"

    return HigherTimeframeTrendContext(
        trends=trends,
        agreement=agreement,
        aligned_direction=aligned_direction,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
    )
