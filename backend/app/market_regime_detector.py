def detect_market_regime(snapshot: dict) -> dict:
    """
    Market Regime Detection V1
    Classifies the current market environment.
    """

    atr_percent = snapshot.get("atr_percent", 0)
    trend = snapshot.get("trend", "Unknown")
    rsi = snapshot.get("rsi", 50)

    regime = "UNKNOWN"
    confidence_adjustment = 0
    preferred_strategies = []
    blocked_strategies = []

    if atr_percent >= 2:
        volatility_regime = "HIGH_VOLATILITY"
    elif atr_percent <= 1:
        volatility_regime = "LOW_VOLATILITY"
    else:
        volatility_regime = "NORMAL_VOLATILITY"

    if trend in ["Bullish", "Bearish"] and atr_percent >= 1:
        regime = "TRENDING"
        preferred_strategies = ["Breakout", "Trend Following", "MA Alignment"]
        blocked_strategies = ["RSI < 30"]
        confidence_adjustment = 3

    elif 35 <= rsi <= 65 and atr_percent < 1.5:
        regime = "RANGING"
        preferred_strategies = ["RSI < 30", "RSI Pullback"]
        blocked_strategies = ["Breakout", "Trend Following"]
        confidence_adjustment = 2

    elif atr_percent >= 2:
        regime = "HIGH_VOLATILITY"
        preferred_strategies = ["Breakout"]
        blocked_strategies = ["RSI < 30"]
        confidence_adjustment = -3

    elif atr_percent <= 1:
        regime = "LOW_VOLATILITY"
        preferred_strategies = ["RSI < 30"]
        blocked_strategies = ["Breakout"]
        confidence_adjustment = -2

    return {
        "market_regime": regime,
        "volatility_regime": volatility_regime,
        "atr_percent": atr_percent,
        "trend": trend,
        "rsi": rsi,
        "preferred_strategies": preferred_strategies,
        "blocked_strategies": blocked_strategies,
        "confidence_adjustment": confidence_adjustment,
        "reason": f"Market classified as {regime} with {volatility_regime}.",
    }