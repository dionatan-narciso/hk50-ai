def calculate_trade_quality_score(market_snapshot, entry_context_score=None):
    score = 50
    reasons = []

    rsi = float(market_snapshot.get("rsi", 0) or 0)
    rsi_slope = market_snapshot.get("rsi_slope", "UNKNOWN")
    trend = market_snapshot.get("trend", "Neutral")
    risk = market_snapshot.get("risk", "Medium")
    ma_alignment = market_snapshot.get("ma_alignment", "UNKNOWN")

    distance_ma20 = float(market_snapshot.get("distance_ma20", 0) or 0)
    distance_ma50 = float(market_snapshot.get("distance_ma50", 0) or 0)
    previous_candle_return = float(
        market_snapshot.get("previous_candle_return", 0) or 0
    )
    trend_strength = float(market_snapshot.get("trend_strength", 0) or 0)

    if rsi_slope == "RISING":
        score += 10
        reasons.append("RSI rising improves quality")

    elif rsi_slope == "FALLING":
        score -= 10
        reasons.append("RSI falling reduces quality")

    if 20 <= rsi <= 35:
        score += 10
        reasons.append("RSI in healthy oversold recovery zone")

    elif rsi < 18:
        score -= 10
        reasons.append("RSI extremely low, risk of falling knife")

    elif rsi > 70:
        score -= 8
        reasons.append("RSI overbought")

    if trend == "Bullish":
        score += 8
        reasons.append("Bullish trend supports entry")

    elif trend == "Bearish":
        score -= 5
        reasons.append("Bearish trend reduces entry quality")

    if risk == "Low":
        score += 8
        reasons.append("Low volatility supports cleaner entry")

    elif risk == "High":
        score -= 8
        reasons.append("High volatility reduces quality")

    if ma_alignment == "BULLISH":
        score += 8
        reasons.append("Bullish MA alignment")

    elif ma_alignment == "BEARISH":
        score -= 5
        reasons.append("Bearish MA alignment")

    if distance_ma20 < -2:
        score += 5
        reasons.append("Price stretched below MA20")

    if distance_ma50 < -2:
        score += 5
        reasons.append("Price stretched below MA50")

    if previous_candle_return <= -0.30:
        score -= 8
        reasons.append("Large negative previous candle")

    if trend_strength >= 1:
        score += 5
        reasons.append("Strong trend structure")

    if entry_context_score:
        score += entry_context_score.get("entry_context_adjustment", 0) * 0.5
        reasons.append("Entry context score included")

    score = round(max(0, min(100, score)), 2)

    if score >= 80:
        label = "EXCELLENT"
    elif score >= 65:
        label = "GOOD"
    elif score >= 50:
        label = "MODERATE"
    else:
        label = "WEAK"

    return {
        "trade_quality_score": score,
        "trade_quality_label": label,
        "trade_quality_reasons": reasons,
    }