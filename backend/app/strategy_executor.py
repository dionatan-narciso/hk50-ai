from app.market_regime_detector import detect_market_regime


def clean_number(value, default=0):
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def execute_trend_following(market_data):
    rsi = clean_number(market_data.get("rsi"), 50)
    trend = market_data.get("trend", "")
    risk = market_data.get("risk", "Medium")

    if trend == "Bullish" and rsi < 70 and risk != "High":
        return "BUY", "Trend following strategy triggered BUY."

    if trend == "Bearish" and rsi > 30 and risk != "High":
        return "SELL", "Trend following strategy triggered SELL."

    return "HOLD", "Trend following strategy found no strong setup."


def execute_rsi_pullback(market_data):
    rsi = clean_number(market_data.get("rsi"), 50)
    trend = market_data.get("trend", "")
    risk = market_data.get("risk", "Medium")

    if trend == "Bullish" and rsi <= 45 and risk != "High":
        return "BUY", "RSI pullback strategy triggered BUY."

    if trend == "Bearish" and rsi >= 55 and risk != "High":
        return "SELL", "RSI pullback strategy triggered SELL."

    return "HOLD", "RSI pullback strategy found no valid pullback."


def execute_ma_alignment(market_data):
    price = clean_number(market_data.get("price"))
    ma20 = clean_number(market_data.get("ma20"))
    ma50 = clean_number(market_data.get("ma50"))
    risk = market_data.get("risk", "Medium")

    if price > ma20 > ma50 and risk != "High":
        return "BUY", "MA alignment strategy triggered BUY."

    if price < ma20 < ma50 and risk != "High":
        return "SELL", "MA alignment strategy triggered SELL."

    return "HOLD", "MA alignment strategy found no strong alignment."


def execute_breakout(market_data):
    trend = market_data.get("trend", "")
    confidence = clean_number(market_data.get("confidence"), 50)
    risk = market_data.get("risk", "Medium")

    if trend == "Bullish" and confidence >= 70 and risk != "High":
        return "BUY", "Breakout strategy triggered BUY."

    if trend == "Bearish" and confidence >= 70 and risk != "High":
        return "SELL", "Breakout strategy triggered SELL."

    return "HOLD", "Breakout strategy found no strong breakout."


def extract_strategy_name(best_strategy):
    if isinstance(best_strategy, dict):
        return str(best_strategy.get("strategy", "")).lower()

    return str(best_strategy).lower()


def is_strategy_blocked_by_regime(strategy_name, regime_data):
    blocked = regime_data.get("blocked_strategies", [])

    if ("rsi<30" in strategy_name or "rsi < 30" in strategy_name) and "RSI < 30" in blocked:
        return True

    if ("rsi" in strategy_name or "pullback" in strategy_name) and "RSI Pullback" in blocked:
        return True

    if ("ma" in strategy_name or "moving" in strategy_name or "alignment" in strategy_name) and "MA Alignment" in blocked:
        return True

    if "breakout" in strategy_name and "Breakout" in blocked:
        return True

    if "trend" in strategy_name and "Trend Following" in blocked:
        return True

    return False


def execute_strategy(best_strategy, market_data):
    strategy_name = extract_strategy_name(best_strategy)
    regime_data = detect_market_regime(market_data)

    if is_strategy_blocked_by_regime(strategy_name, regime_data):
        return {
            "strategy_used": best_strategy,
            "signal": "HOLD",
            "strategy_reason": (
                f"Strategy blocked by market regime. "
                f"{regime_data.get('reason')}"
            ),
            "market_regime": regime_data,
        }

    if "rsi<30" in strategy_name or "rsi < 30" in strategy_name:
        rsi = clean_number(market_data.get("rsi"), 50)
        risk = market_data.get("risk", "Medium")

        if rsi < 30 and risk != "High":
            signal = "BUY"
            reason = "RSI < 30 strategy triggered BUY."
        else:
            signal = "HOLD"
            reason = "RSI < 30 strategy found no valid setup."

    elif "rsi" in strategy_name or "pullback" in strategy_name:
        signal, reason = execute_rsi_pullback(market_data)

    elif "ma" in strategy_name or "moving" in strategy_name or "alignment" in strategy_name:
        signal, reason = execute_ma_alignment(market_data)

    elif "breakout" in strategy_name:
        signal, reason = execute_breakout(market_data)

    elif "trend" in strategy_name:
        signal, reason = execute_trend_following(market_data)

    else:
        signal, reason = execute_trend_following(market_data)

    return {
        "strategy_used": best_strategy,
        "signal": signal,
        "strategy_reason": reason,
        "market_regime": regime_data,
    }