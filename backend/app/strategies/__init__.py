"""Strategy plugin contracts, adapters, registry, and parity voting.

Sprint 1A introduces these abstractions incrementally. Adapters and
registry-driven voting are parity-tested before production wiring is switched.
"""

from app.strategies.breakout import BreakoutStrategy
from app.strategies.contracts import MarketContext, Strategy, StrategyDecision
from app.strategies.default_registry import build_default_strategy_registry
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.registry import StrategyRegistry
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.voting import run_registry_strategy_vote

__all__ = [
    "BreakoutStrategy",
    "MaAlignmentStrategy",
    "MarketContext",
    "RsiPullbackStrategy",
    "Strategy",
    "StrategyDecision",
    "StrategyRegistry",
    "TrendFollowingStrategy",
    "build_default_strategy_registry",
    "run_registry_strategy_vote",
]
