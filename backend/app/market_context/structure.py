from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.strategies.numbers import clean_number


@dataclass(frozen=True)
class MarketStructureContext:
    """Objective price/MA structure for one market snapshot.

    Sprint 1B.6 deliberately avoids support/resistance or extension thresholds.
    It records observable relationships only so later replay research can decide
    whether any of them deserve predictive weight.
    """

    directional_structure: str
    price_position: str
    ma_alignment: str
    distance_to_ma20_percent: float | None
    distance_to_ma50_percent: float | None
    nearest_anchor: str | None
    nearest_anchor_distance_percent: float | None


def calculate_signed_distance_percent(price: Any, anchor: Any) -> float | None:
    """Return signed percentage distance from an anchor using price as denominator."""
    price_value = clean_number(price, 0)
    anchor_value = clean_number(anchor, 0)

    if price_value <= 0 or anchor_value <= 0:
        return None

    return (price_value - anchor_value) / price_value * 100


def classify_ma_alignment(ma20: Any, ma50: Any) -> str:
    ma20_value = clean_number(ma20, 0)
    ma50_value = clean_number(ma50, 0)

    if ma20_value <= 0 or ma50_value <= 0:
        return "UNKNOWN"
    if ma20_value > ma50_value:
        return "BULLISH"
    if ma20_value < ma50_value:
        return "BEARISH"
    return "FLAT"


def classify_price_position(price: Any, ma20: Any, ma50: Any) -> str:
    price_value = clean_number(price, 0)
    ma20_value = clean_number(ma20, 0)
    ma50_value = clean_number(ma50, 0)

    if price_value <= 0 or ma20_value <= 0 or ma50_value <= 0:
        return "UNKNOWN"
    if price_value > max(ma20_value, ma50_value):
        return "ABOVE_BOTH"
    if price_value < min(ma20_value, ma50_value):
        return "BELOW_BOTH"
    if price_value == ma20_value or price_value == ma50_value:
        return "AT_MA"
    return "BETWEEN_MAS"


def classify_directional_structure(price: Any, ma20: Any, ma50: Any) -> str:
    price_value = clean_number(price, 0)
    ma20_value = clean_number(ma20, 0)
    ma50_value = clean_number(ma50, 0)

    if price_value <= 0 or ma20_value <= 0 or ma50_value <= 0:
        return "UNKNOWN"
    if price_value > ma20_value > ma50_value:
        return "BULLISH_STACK"
    if price_value < ma20_value < ma50_value:
        return "BEARISH_STACK"
    return "MIXED"


def derive_market_structure_context(
    snapshot: Mapping[str, Any],
) -> MarketStructureContext:
    """Derive objective primary-timeframe structure from price, MA20, and MA50."""
    price = clean_number(snapshot.get("price"), 0)
    ma20 = clean_number(snapshot.get("ma20"), 0)
    ma50 = clean_number(snapshot.get("ma50"), 0)

    distance_ma20 = calculate_signed_distance_percent(price, ma20)
    distance_ma50 = calculate_signed_distance_percent(price, ma50)

    nearest_anchor = None
    nearest_distance = None
    if distance_ma20 is not None and distance_ma50 is not None:
        absolute_ma20 = abs(distance_ma20)
        absolute_ma50 = abs(distance_ma50)
        if absolute_ma20 <= absolute_ma50:
            nearest_anchor = "MA20"
            nearest_distance = absolute_ma20
        else:
            nearest_anchor = "MA50"
            nearest_distance = absolute_ma50

    return MarketStructureContext(
        directional_structure=classify_directional_structure(price, ma20, ma50),
        price_position=classify_price_position(price, ma20, ma50),
        ma_alignment=classify_ma_alignment(ma20, ma50),
        distance_to_ma20_percent=distance_ma20,
        distance_to_ma50_percent=distance_ma50,
        nearest_anchor=nearest_anchor,
        nearest_anchor_distance_percent=nearest_distance,
    )
