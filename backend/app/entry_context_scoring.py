from app.entry_learning_memory import load_entry_weights


def calculate_entry_context_score(market_snapshot, entry_weights_override=None):
    if entry_weights_override is not None:
        weights = entry_weights_override
    else:
        weights = load_entry_weights()

    score_adjustment = 0
    reasons = []

    rsi = float(market_snapshot.get("rsi", 0) or 0)
    rsi_slope = market_snapshot.get("rsi_slope", "UNKNOWN")

    previous_candle_return = float(
        market_snapshot.get("previous_candle_return", 0) or 0
    )

    distance_ma20 = float(
        market_snapshot.get("distance_ma20", 0) or 0
    )

    distance_ma50 = float(
        market_snapshot.get("distance_ma50", 0) or 0
    )

    if rsi_slope == "RISING":
        value = weights["rsi_rising_bonus"]
        score_adjustment += value
        reasons.append(f"RSI rising bonus {value}")

    elif rsi_slope == "FALLING":
        value = weights["rsi_falling_penalty"]
        score_adjustment += value
        reasons.append(f"RSI falling penalty {value}")

    if previous_candle_return <= -0.30:
        value = weights["negative_candle_penalty"]
        score_adjustment += value
        reasons.append(f"Large negative previous candle penalty {value}")

    if distance_ma20 < -2:
        value = weights["ma20_stretch_bonus"]
        score_adjustment += value
        reasons.append(f"Price stretched below MA20 bonus {value}")

    if distance_ma50 < -2:
        value = weights["ma50_stretch_bonus"]
        score_adjustment += value
        reasons.append(f"Price stretched below MA50 bonus {value}")

    if rsi < 18:
        value = weights["extreme_rsi_penalty"]
        score_adjustment += value
        reasons.append(f"Extreme RSI below 18 penalty {value}")

    return {
        "entry_context_adjustment": score_adjustment,
        "entry_context_reasons": reasons,
        "entry_weights_used": weights,
    }