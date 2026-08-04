"""Strategy plugin contracts, adapters, and registry.

Sprint 1A introduces these abstractions incrementally. Adapters are added and
parity-tested before production voting is switched to the plugin registry.
"""

from app.strategies.contracts import MarketContext, Strategy, StrategyDecision
from app.strategies.registry import StrategyRegistry
from app.strategies.rsi_pullback import RsiPullbackStrategy

__all__ = [
    "MarketContext",
    "RsiPullbackStrategy",
    "Strategy",
    "StrategyDecision",
    "StrategyRegistry",
]
