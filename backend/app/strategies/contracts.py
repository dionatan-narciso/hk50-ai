from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from app.strategies.metadata import StrategyMetadata


VALID_SIGNALS = frozenset({"BUY", "SELL", "HOLD"})


@dataclass(frozen=True)
class MarketContext:
    """Market-independent input supplied to a strategy plugin.

    ``data`` remains the canonical primary-timeframe mapping used by the current
    strategies. The additional mappings are optional enrichment containers for
    Sprint 1B and default to empty so existing callers and trading behaviour are
    unchanged.
    """

    symbol: str
    timeframe: str
    data: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    higher_timeframes: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    regime: Mapping[str, Any] = field(default_factory=dict)
    session: Mapping[str, Any] = field(default_factory=dict)
    structure: Mapping[str, Any] = field(default_factory=dict)
    features: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Read a primary-timeframe value using the established dictionary API."""
        return self.data.get(key, default)

    def get_timeframe(
        self,
        timeframe: str,
        default: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Return enriched data for another timeframe without altering primary data."""
        if default is None:
            default = {}
        return self.higher_timeframes.get(timeframe, default)

    def get_feature(self, key: str, default: Any = None) -> Any:
        """Read a derived market feature from the enrichment namespace."""
        return self.features.get(key, default)


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
