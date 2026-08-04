"""Strategy plugin contracts, adapters, and registry.

Sprint 1A introduces these abstractions incrementally. Adapters are added and
parity-tested before production voting is switched to the plugin registry.
"""

from app.strategies.breakout import BreakoutStrategy
from app.strategies.contracts import MarketContext, Strategy, StrategyDecision
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.registry import StrategyRegistry
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy

__all__ = [
    "BreakoutStrategy",
    "MaAlignmentStrategy",
    "MarketContext",
    "RsiPullbackStrategy",
    "Strategy",
    "StrategyDecision",
    "StrategyRegistry",
    "TrendFollowingStrategy",
]
