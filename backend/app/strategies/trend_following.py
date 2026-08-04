from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.numbers import clean_number


class TrendFollowingStrategy:
    """Trend Following strategy plugin preserving the established rules."""

    @property
    def name(self) -> str:
        return "Trend Following"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        rsi = clean_number(context.get("rsi"), 50)
        trend = context.get("trend", "")
        risk = context.get("risk", "Medium")

        if trend == "Bullish" and rsi < 70 and risk != "High":
            signal = "BUY"
            reason = "Trend following strategy triggered BUY."
        elif trend == "Bearish" and rsi > 30 and risk != "High":
            signal = "SELL"
            reason = "Trend following strategy triggered SELL."
        else:
            signal = "HOLD"
            reason = "Trend following strategy found no strong setup."

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
