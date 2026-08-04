from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategy_executor import execute_ma_alignment


class MaAlignmentStrategy:
    """Plugin adapter for the existing MA Alignment strategy."""

    @property
    def name(self) -> str:
        return "MA Alignment"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        signal, reason = execute_ma_alignment(context.data)

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
