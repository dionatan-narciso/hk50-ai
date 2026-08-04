from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategy_executor import execute_rsi_pullback


class RsiPullbackStrategy:
    """Plugin adapter for the existing RSI Pullback strategy.

    This adapter deliberately delegates to the legacy execution function so the
    first migration step changes no thresholds, signals, or reason wording.
    """

    @property
    def name(self) -> str:
        return "RSI Pullback"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        signal, reason = execute_rsi_pullback(context.data)

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
