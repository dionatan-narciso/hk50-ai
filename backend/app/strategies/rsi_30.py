from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.numbers import clean_number


class Rsi30Strategy:
    """Plugin implementation of the existing RSI < 30 strategy."""

    @property
    def name(self) -> str:
        return "RSI < 30"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        rsi = clean_number(context.get("rsi"), 50)
        risk = context.get("risk", "Medium")

        if rsi < 30 and risk != "High":
            signal = "BUY"
            reason = "RSI < 30 strategy triggered BUY."
        else:
            signal = "HOLD"
            reason = "RSI < 30 strategy found no valid setup."

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
