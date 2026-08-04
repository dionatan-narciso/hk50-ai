"""Strategy plugin contracts, implementations, registries, and voting."""

from app.strategies.breakout import BreakoutStrategy
from app.strategies.contracts import MarketContext, Strategy, StrategyDecision
from app.strategies.default_registry import (
    build_default_strategy_registry,
    build_execution_strategy_registry,
)
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.registry import StrategyRegistry
from app.strategies.resolution import (
    extract_strategy_name,
    is_strategy_blocked_by_regime,
    resolve_registered_strategy_name,
)
from app.strategies.rsi_30 import Rsi30Strategy
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.voting import run_registry_strategy_vote

__all__ = [
    "BreakoutStrategy",
    "MaAlignmentStrategy",
    "MarketContext",
    "Rsi30Strategy",
    "RsiPullbackStrategy",
    "Strategy",
    "StrategyDecision",
    "StrategyRegistry",
    "TrendFollowingStrategy",
    "build_default_strategy_registry",
    "build_execution_strategy_registry",
    "extract_strategy_name",
    "is_strategy_blocked_by_regime",
    "resolve_registered_strategy_name",
    "run_registry_strategy_vote",
]
