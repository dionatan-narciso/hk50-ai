from app.strategies.breakout import BreakoutStrategy
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.registry import StrategyRegistry
from app.strategies.rsi_30 import Rsi30Strategy
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from app.strategies.validation import validate_strategy_registry


DEFAULT_SYMBOL = "HK50"
DEFAULT_TIMEFRAME = "1h"


def build_default_strategy_registry() -> StrategyRegistry:
    """Build and validate the ordered registry used by strategy voting."""
    registry = StrategyRegistry(
        [
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
        ]
    )
    return validate_strategy_registry(
        registry,
        symbol=DEFAULT_SYMBOL,
        timeframe=DEFAULT_TIMEFRAME,
        require_voting_eligible=True,
    )


def build_execution_strategy_registry() -> StrategyRegistry:
    """Build and validate selected-strategy execution plugins."""
    registry = StrategyRegistry(
        [
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        ]
    )
    return validate_strategy_registry(
        registry,
        symbol=DEFAULT_SYMBOL,
        timeframe=DEFAULT_TIMEFRAME,
    )
