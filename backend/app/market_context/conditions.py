from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.strategies.numbers import clean_number


@dataclass(frozen=True)
class MarketConditionContext:
    """Informational volatility and trend-strength description for one snapshot."""

    volatility: str
    atr_percent: float
    trend_strength: str
    ma_separation_percent: float | None
    trend: str


def classify_volatility(atr_percent: Any) -> str:
    """Use the existing production volatility thresholds without changing them."""
    value = clean_number(atr_percent, 0)

    if value >= 2:
        return "HIGH_VOLATILITY"
    if value <= 1:
        return "LOW_VOLATILITY"
    return "NORMAL_VOLATILITY"


def calculate_ma_separation_percent(snapshot: Mapping[str, Any]) -> float | None:
    """Return absolute MA20/MA50 separation as a percentage of price."""
    price = clean_number(snapshot.get("price"), 0)
    ma20 = clean_number(snapshot.get("ma20"), 0)
    ma50 = clean_number(snapshot.get("ma50"), 0)

    if price <= 0 or ma20 <= 0 or ma50 <= 0:
        return None

    return abs(ma20 - ma50) / price * 100


def classify_trend_strength(ma_separation_percent: float | None) -> str:
    """Describe MA separation without affecting trading decisions.

    Sprint 1B.5 V1 thresholds are deliberately simple and informational. They
    can be validated or replaced through replay research before any strategy or
    confidence engine is allowed to consume them.
    """
    if ma_separation_percent is None:
        return "UNKNOWN"
    if ma_separation_percent < 0.1:
        return "FLAT"
    if ma_separation_percent < 0.5:
        return "WEAK"
    if ma_separation_percent < 1.0:
        return "MODERATE"
    return "STRONG"


def derive_market_condition_context(
    snapshot: Mapping[str, Any],
) -> MarketConditionContext:
    """Derive informational volatility and trend-strength context."""
    atr_percent = clean_number(snapshot.get("atr_percent"), 0)
    separation = calculate_ma_separation_percent(snapshot)

    return MarketConditionContext(
        volatility=classify_volatility(atr_percent),
        atr_percent=atr_percent,
        trend_strength=classify_trend_strength(separation),
        ma_separation_percent=separation,
        trend=str(snapshot.get("trend", "Unknown")),
    )
