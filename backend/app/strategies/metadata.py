from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyMetadata:
    """Declarative capabilities for a strategy plugin.

    Metadata is informational in Sprint 1A.9. Existing voting and execution
    registries continue to control behavior explicitly.
    """

    version: str = "1.0.0"
    supported_markets: tuple[str, ...] = ("HK50",)
    supported_timeframes: tuple[str, ...] = ("1h",)
    voting_eligible: bool = True

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("Strategy version cannot be empty.")
        if not self.supported_markets:
            raise ValueError("Strategy must support at least one market.")
        if not self.supported_timeframes:
            raise ValueError("Strategy must support at least one timeframe.")
        if any(not value.strip() for value in self.supported_markets):
            raise ValueError("Supported market names cannot be empty.")
        if any(not value.strip() for value in self.supported_timeframes):
            raise ValueError("Supported timeframe names cannot be empty.")

    def supports(self, symbol: str, timeframe: str) -> bool:
        return symbol in self.supported_markets and timeframe in self.supported_timeframes
