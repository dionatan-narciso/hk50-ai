def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def calculate_trade_context(market_data):
    close = safe_float(
        market_data.get("close")
        or market_data.get("Close")
        or market_data.get("price")
        or market_data.get("current_price")
    )

    ma20 = safe_float(
        market_data.get("ma20")
        or market_data.get("MA20")
    )

    ma50 = safe_float(
        market_data.get("ma50")
        or market_data.get("MA50")
    )

    previous_close = safe_float(
        market_data.get("previous_close")
        or market_data.get("Previous Close")
        or close
    )

    rsi = safe_float(
        market_data.get("rsi")
        or market_data.get("RSI")
    )

    previous_rsi = safe_float(
        market_data.get("previous_rsi")
        or market_data.get("Previous RSI")
        or rsi
    )

    distance_ma20 = ((close - ma20) / ma20) * 100 if ma20 else 0
    distance_ma50 = ((close - ma50) / ma50) * 100 if ma50 else 0
    previous_candle_return = (
        ((close - previous_close) / previous_close) * 100
        if previous_close
        else 0
    )

    trend_strength = abs(distance_ma20 - distance_ma50)

    if ma20 > ma50:
        ma_alignment = "BULLISH"
    elif ma20 < ma50:
        ma_alignment = "BEARISH"
    else:
        ma_alignment = "NEUTRAL"

    if rsi > previous_rsi:
        rsi_slope = "RISING"
    elif rsi < previous_rsi:
        rsi_slope = "FALLING"
    else:
        rsi_slope = "FLAT"

    return {
        "close_at_entry": round(close, 3),
        "ma20_at_entry": round(ma20, 3),
        "ma50_at_entry": round(ma50, 3),
        "distance_ma20": round(distance_ma20, 3),
        "distance_ma50": round(distance_ma50, 3),
        "previous_candle_return": round(previous_candle_return, 3),
        "trend_strength": round(trend_strength, 3),
        "ma_alignment": ma_alignment,
        "rsi_slope": rsi_slope,
    }