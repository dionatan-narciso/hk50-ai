from app.strategy_executor import (
    execute_rsi_pullback,
    execute_ma_alignment,
    execute_breakout,
    execute_trend_following,
)


def run_strategy_vote(market_data):
    votes = []

    strategies = [
        ("RSI Pullback", execute_rsi_pullback),
        ("MA Alignment", execute_ma_alignment),
        ("Breakout", execute_breakout),
        ("Trend Following", execute_trend_following),
    ]

    for name, strategy_function in strategies:
        signal, reason = strategy_function(market_data)

        votes.append({
            "strategy": name,
            "signal": signal,
            "reason": reason,
        })

    buy_votes = len([v for v in votes if v["signal"] == "BUY"])
    sell_votes = len([v for v in votes if v["signal"] == "SELL"])
    hold_votes = len([v for v in votes if v["signal"] == "HOLD"])

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