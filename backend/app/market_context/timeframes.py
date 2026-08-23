from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.strategies.contracts import MarketContext


@dataclass(frozen=True)
class TimeframeSnapshot:
    """Analyzed market values for one symbol/timeframe at one logical point in time."""

    symbol: str
    timeframe: str
    data: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Timeframe snapshot symbol cannot be empty.")
        if not self.timeframe.strip():
            raise ValueError("Timeframe snapshot timeframe cannot be empty.")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def build_market_context(
    primary: TimeframeSnapshot,
    *higher_timeframes: TimeframeSnapshot,
    metadata: Mapping[str, Any] | None = None,
    regime: Mapping[str, Any] | None = None,
    session: Mapping[str, Any] | None = None,
    structure: Mapping[str, Any] | None = None,
    features: Mapping[str, Any] | None = None,
) -> MarketContext:
    """Assemble one primary snapshot plus optional higher-timeframe snapshots.

    The primary snapshot remains the exact mapping consumed by existing
    strategies. Higher timeframes are namespaced and therefore cannot affect
    current decisions until a strategy explicitly opts in to reading them.
    """
    enriched: dict[str, Mapping[str, Any]] = {}

    for snapshot in higher_timeframes:
        if snapshot.symbol != primary.symbol:
            raise ValueError(
                "Higher-timeframe snapshot symbol must match primary symbol: "
                f"{snapshot.symbol!r} != {primary.symbol!r}."
            )
        if snapshot.timeframe == primary.timeframe:
            raise ValueError(
                f"Higher-timeframe snapshot duplicates primary timeframe {primary.timeframe!r}."
            )
        if snapshot.timeframe in enriched:
            raise ValueError(
                f"Duplicate higher-timeframe snapshot {snapshot.timeframe!r}."
            )
        enriched[snapshot.timeframe] = snapshot.data

    context_metadata = dict(primary.metadata)
    if metadata:
        context_metadata.update(metadata)

    return MarketContext(
        symbol=primary.symbol,
        timeframe=primary.timeframe,
        data=primary.data,
        metadata=context_metadata,
        higher_timeframes=enriched,
        regime=regime or {},
        session=session or {},
        structure=structure or {},
        features=features or {},
    )
