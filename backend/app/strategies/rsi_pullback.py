from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.metadata import StrategyMetadata
from app.strategies.numbers import clean_number


class RsiPullbackStrategy:
    """RSI Pullback strategy plugin preserving the established rules."""

    metadata = StrategyMetadata()

    @property
    def name(self) -> str:
        return "RSI Pullback"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        rsi = clean_number(context.get("rsi"), 50)
        trend = context.get("trend", "")
        risk = context.get("risk", "Medium")

        if trend == "Bullish" and rsi <= 45 and risk != "High":
            signal = "BUY"
            reason = "RSI pullback strategy triggered BUY."
        elif trend == "Bearish" and rsi >= 55 and risk != "High":
            signal = "SELL"
            reason = "RSI pullback strategy triggered SELL."
        else:
            signal = "HOLD"
            reason = "RSI pullback strategy found no valid pullback."

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
