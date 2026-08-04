from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.numbers import clean_number


class BreakoutStrategy:
    """Breakout strategy plugin preserving the established rules."""

    @property
    def name(self) -> str:
        return "Breakout"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        trend = context.get("trend", "")
        confidence = clean_number(context.get("confidence"), 50)
        risk = context.get("risk", "Medium")

        if trend == "Bullish" and confidence >= 70 and risk != "High":
            signal = "BUY"
            reason = "Breakout strategy triggered BUY."
        elif trend == "Bearish" and confidence >= 70 and risk != "High":
            signal = "SELL"
            reason = "Breakout strategy triggered SELL."
        else:
            signal = "HOLD"
            reason = "Breakout strategy found no strong breakout."

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
