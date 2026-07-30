from datetime import datetime

from app.paper_trade_journal_repository import load_paper_trade_journal


def get_today_trades():
    df = load_paper_trade_journal()

    if df.empty or "closed_at" not in df.columns:
        return []

    today = datetime.now().strftime("%Y-%m-%d")

    df["closed_date"] = df["closed_at"].astype(str).str[:10]
    today_df = df[df["closed_date"] == today]

    return today_df.to_dict("records")


def check_daily_risk_limits():
    today_trades = get_today_trades()

    total_trades = len(today_trades)
    losses = [
        trade for trade in today_trades
        if float(trade.get("return_percent", 0)) <= 0
    ]

    daily_return = sum(
        float(trade.get("return_percent", 0))
        for trade in today_trades
    )

    if total_trades >= 5:
        return {
            "allow_trade": False,
            "reason": "Daily trade limit reached.",
            "daily_trades": total_trades,
            "daily_losses": len(losses),
            "daily_return": round(daily_return, 3),
        }

    if len(losses) >= 3:
        return {
            "allow_trade": False,
            "reason": "Daily loss limit reached.",
            "daily_trades": total_trades,
            "daily_losses": len(losses),
            "daily_return": round(daily_return, 3),
        }

    if daily_return <= -2:
        return {
            "allow_trade": False,
            "reason": "Daily drawdown limit reached.",
            "daily_trades": total_trades,
            "daily_losses": len(losses),
            "daily_return": round(daily_return, 3),
        }

    return {
        "allow_trade": True,
        "reason": "Daily risk limits allow trading.",
        "daily_trades": total_trades,
        "daily_losses": len(losses),
        "daily_return": round(daily_return, 3),
    }
