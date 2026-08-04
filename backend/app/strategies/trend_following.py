from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategy_executor import execute_trend_following


class TrendFollowingStrategy:
    """Plugin adapter for the existing Trend Following strategy."""

    @property
    def name(self) -> str:
        return "Trend Following"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        signal, reason = execute_trend_following(context.data)

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
