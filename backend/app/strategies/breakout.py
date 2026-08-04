from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategy_executor import execute_breakout


class BreakoutStrategy:
    """Plugin adapter for the existing Breakout strategy."""

    @property
    def name(self) -> str:
        return "Breakout"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        signal, reason = execute_breakout(context.data)

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
