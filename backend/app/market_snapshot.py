from datetime import datetime
import random

# Phase 1 uses realistic sample data so the React UI can be built first.
# Phase 2 will replace this with the existing Python trading engine from app.py.

def get_market_snapshot():
    price = 23047.82 + random.uniform(-25, 25)
    confidence = 72 + random.uniform(-4, 4)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": "HK50 / Hang Seng",
        "price": round(price, 2),
        "change_percent": round(random.uniform(-0.45, 0.75), 2),
        "signal": "BUY" if confidence >= 70 else "WAIT",
        "confidence": round(confidence, 1),
        "trend": "Bullish Alignment",
        "risk": "Medium",
        "atr_percent": 0.87,
        "setup": "Bullish Trend Continuation",
        "regime": "Momentum Expansion",
        "sentiment": "Neutral",
        "timeframes": [
            {"label": "15m", "trend": "Bullish", "score": 70},
            {"label": "1h", "trend": "Bullish", "score": 74},
            {"label": "4h", "trend": "Mixed", "score": 54},
            {"label": "1D", "trend": "Bullish", "score": 71},
        ],
        "indicators": [
            {"name": "RSI", "value": "58.4", "state": "Neutral"},
            {"name": "MACD", "value": "Bullish", "state": "Increasing"},
            {"name": "Volume", "value": "1.18x", "state": "Normal"},
            {"name": "Structure", "value": "72/100", "state": "Supportive"},
        ],
        "strategyLeaderboard": [
            {"strategy": "Best So Far", "pl": 4.82, "winRate": 64.2, "trades": 28},
            {"strategy": "Aggressive Momentum", "pl": 3.91, "winRate": 59.8, "trades": 36},
            {"strategy": "RSI Pullback", "pl": 2.44, "winRate": 57.1, "trades": 21},
            {"strategy": "Conservative Trend", "pl": 1.18, "winRate": 61.0, "trades": 11},
        ],
        "latestSignals": [
            {"time": "10:15", "signal": "BUY", "score": 73, "price": 23042.1},
            {"time": "09:00", "signal": "WAIT", "score": 61, "price": 22980.4},
            {"time": "08:00", "signal": "WAIT", "score": 58, "price": 22955.8},
        ],
        "candles": [
            {"time": i, "open": 22800 + i*8 + random.uniform(-20, 20), "high": 22835 + i*8 + random.uniform(-20, 35), "low": 22770 + i*8 + random.uniform(-35, 10), "close": 22810 + i*8 + random.uniform(-25, 25)}
            for i in range(48)
        ],
    }
