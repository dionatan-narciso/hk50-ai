from app.strategies.breakout import BreakoutStrategy
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.registry import StrategyRegistry
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy


def build_default_strategy_registry() -> StrategyRegistry:
    """Build the ordered registry matching the current voting-engine order."""
    return StrategyRegistry(
        [
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
        ]
    )
