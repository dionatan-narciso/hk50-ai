from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from app.strategies.metadata import StrategyMetadata


VALID_SIGNALS = frozenset({"BUY", "SELL", "HOLD"})


@dataclass(frozen=True)
class MarketContext:
    """Market-independent input supplied to a strategy plugin.

    The raw mapping preserves the existing market-data contract while explicit
    identity fields prepare the platform for multiple symbols and timeframes.
    """

    symbol: str
    timeframe: str
    data: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a value using the same pattern as the current market dictionary."""
        return self.data.get(key, default)


@dataclass(frozen=True)
class StrategyDecision:
    """Standard result returned by every strategy plugin."""

    strategy: str
    signal: str
    reason: str
    confidence: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_signal = self.signal.upper()
        if normalized_signal not in VALID_SIGNALS:
            raise ValueError(
                f"Unsupported strategy signal {self.signal!r}; "
                f"expected one of {sorted(VALID_SIGNALS)}."
            )
        object.__setattr__(self, "signal", normalized_signal)

        if self.confidence is not None and not 0 <= self.confidence <= 100:
            raise ValueError("Strategy confidence must be between 0 and 100.")


@runtime_checkable
class Strategy(Protocol):
    """Structural interface implemented by strategy plugins."""

    @property
    def name(self) -> str:
        ...

    @property
    def metadata(self) -> StrategyMetadata:
        ...

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        ...
