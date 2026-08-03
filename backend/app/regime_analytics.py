from app.regime_performance_memory import load_regime_performance


def get_regime_bonus(strategy, market_regime, volatility_regime):
    df = load_regime_performance()

    if df.empty:
        return {
            "regime_bonus": 0,
            "reason": "No regime performance data yet."
        }

    match = df[
        (df["strategy"] == strategy)
        & (df["market_regime"] == market_regime)
        & (df["volatility_regime"] == volatility_regime)
    ]

    if match.empty:
        return {
            "regime_bonus": 0,
            "reason": "No regime history for this strategy and market condition yet."
        }

    row = match.iloc[0]

    trades = int(row.get("trades", 0))
    wins = int(row.get("wins", 0))
    average_return = float(row.get("average_return", 0))

    win_rate = (wins / trades) * 100 if trades > 0 else 0

    if trades < 3:
        return {
            "regime_bonus": 0,
            "reason": (
                f"Only {trades} regime trade(s) recorded. "
                "Not enough data for regime confidence adjustment yet."
            )
        }

    if win_rate >= 70 and average_return > 0.5:
        return {
            "regime_bonus": 8,
            "reason": (
                f"Strong regime performance. Win rate {round(win_rate, 1)}%, "
                f"average return {average_return}%."
            )
        }

    if win_rate >= 60 and average_return > 0:
        return {
            "regime_bonus": 5,
            "reason": (
                f"Positive regime performance. Win rate {round(win_rate, 1)}%, "
                f"average return {average_return}%."
            )
        }

    if win_rate < 45 or average_return < 0:
        return {
            "regime_bonus": -8,
            "reason": (
                f"Weak regime performance. Win rate {round(win_rate, 1)}%, "
                f"average return {average_return}%."
            )
        }

    return {
        "regime_bonus": 0,
        "reason": (
            f"Neutral regime performance. Win rate {round(win_rate, 1)}%, "
            f"average return {average_return}%."
        )
    }
