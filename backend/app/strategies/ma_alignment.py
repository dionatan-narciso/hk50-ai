from app.strategies.contracts import MarketContext, StrategyDecision
from app.strategies.numbers import clean_number


class MaAlignmentStrategy:
    """MA Alignment strategy plugin preserving the established rules."""

    @property
    def name(self) -> str:
        return "MA Alignment"

    def evaluate(self, context: MarketContext) -> StrategyDecision:
        price = clean_number(context.get("price"))
        ma20 = clean_number(context.get("ma20"))
        ma50 = clean_number(context.get("ma50"))
        risk = context.get("risk", "Medium")

        if price > ma20 > ma50 and risk != "High":
            signal = "BUY"
            reason = "MA alignment strategy triggered BUY."
        elif price < ma20 < ma50 and risk != "High":
            signal = "SELL"
            reason = "MA alignment strategy triggered SELL."
        else:
            signal = "HOLD"
            reason = "MA alignment strategy found no strong alignment."

        return StrategyDecision(
            strategy=self.name,
            signal=signal,
            reason=reason,
        )
