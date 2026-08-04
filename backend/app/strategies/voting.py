from __future__ import annotations

from typing import Any, Mapping

from app.strategies.contracts import MarketContext
from app.strategies.default_registry import build_default_strategy_registry
from app.strategies.registry import StrategyRegistry


def run_registry_strategy_vote(
    market_data: Mapping[str, Any],
    registry: StrategyRegistry | None = None,
    *,
    symbol: str = "HK50",
    timeframe: str = "1h",
) -> dict[str, Any]:
    """Run strategy voting through plugins while preserving the legacy response."""
    active_registry = registry or build_default_strategy_registry()
    context = MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        data=market_data,
    )

    votes = []
    for strategy in active_registry.all():
        decision = strategy.evaluate(context)
        votes.append(
            {
                "strategy": decision.strategy,
                "signal": decision.signal,
                "reason": decision.reason,
            }
        )

    buy_votes = len([vote for vote in votes if vote["signal"] == "BUY"])
    sell_votes = len([vote for vote in votes if vote["signal"] == "SELL"])
    hold_votes = len([vote for vote in votes if vote["signal"] == "HOLD"])

    if buy_votes > sell_votes and buy_votes >= 2:
        final_vote = "BUY"
        vote_strength = buy_votes
    elif sell_votes > buy_votes and sell_votes >= 2:
        final_vote = "SELL"
        vote_strength = sell_votes
    else:
        final_vote = "HOLD"
        vote_strength = hold_votes

    return {
        "votes": votes,
        "buy_votes": buy_votes,
        "sell_votes": sell_votes,
        "hold_votes": hold_votes,
        "final_vote": final_vote,
        "vote_strength": vote_strength,
        "total_votes": len(votes),
    }
