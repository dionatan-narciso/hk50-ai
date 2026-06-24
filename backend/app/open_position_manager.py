from datetime import datetime
from app.automatic_signal_tracker import load_open_position


def calculate_time_open(opened_at):
    try:
        opened_time = datetime.strptime(opened_at, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()

        minutes_open = int((now - opened_time).total_seconds() / 60)

        if minutes_open < 60:
            return f"{minutes_open}m"

        hours = minutes_open // 60
        minutes = minutes_open % 60

        return f"{hours}h {minutes}m"

    except Exception:
        return "Unknown"


def get_open_position_status(current_price, position_size=None):
    open_position = load_open_position()

    if not open_position:
        return {
            "has_open_position": False,
            "status": "IDLE",
            "message": "No open position"
        }

    entry_price = float(open_position.get("entry_price", 0))
    direction = open_position.get("signal", "UNKNOWN")

    unrealised_return = ((current_price - entry_price) / entry_price) * 100

    if direction == "SELL":
        unrealised_return = unrealised_return * -1

    return {
        "has_open_position": True,
        "status": "ACTIVE",
        "symbol": open_position.get("symbol", "HK50"),
        "direction": direction,
        "entry_price": entry_price,
        "current_price": current_price,
        "unrealised_return": round(unrealised_return, 3),
        "strategy": open_position.get("reason", "Unknown"),
        "confidence": open_position.get("confidence", 0),
        "position_size": position_size,
        "opened_at": open_position.get("opened_at"),
        "peak_profit_percent": open_position.get("peak_profit_percent", 0),
        "trailing_active": open_position.get("trailing_active", False),
        "time_open": calculate_time_open(open_position.get("opened_at")),
    }