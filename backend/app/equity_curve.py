import os
import pandas as pd

TRADE_JOURNAL_FILE = "data/trade_journal.csv"
STARTING_EQUITY = 10000


def run_equity_curve():
    if not os.path.exists(TRADE_JOURNAL_FILE):
        return {
            "starting_equity": STARTING_EQUITY,
            "current_equity": STARTING_EQUITY,
            "total_return": 0,
            "max_drawdown": 0,
            "equity_history": []
        }

    df = pd.read_csv(TRADE_JOURNAL_FILE)

    if df.empty or "result_pct" not in df.columns:
        return {
            "starting_equity": STARTING_EQUITY,
            "current_equity": STARTING_EQUITY,
            "total_return": 0,
            "max_drawdown": 0,
            "equity_history": []
        }

    equity = STARTING_EQUITY
    peak_equity = STARTING_EQUITY
    max_drawdown = 0
    history = []

    for _, trade in df.iterrows():
        result_pct = float(trade.get("result_pct", 0))

        equity = equity * (1 + result_pct / 100)
        peak_equity = max(peak_equity, equity)

        drawdown = ((equity - peak_equity) / peak_equity) * 100
        max_drawdown = min(max_drawdown, drawdown)

        history.append({
            "timestamp": trade.get("timestamp", ""),
            "strategy": trade.get("strategy", ""),
            "result_pct": round(result_pct, 3),
            "equity": round(equity, 2),
            "drawdown": round(drawdown, 3)
        })

    total_return = ((equity - STARTING_EQUITY) / STARTING_EQUITY) * 100

    return {
        "starting_equity": STARTING_EQUITY,
        "current_equity": round(equity, 2),
        "peak_equity": round(peak_equity, 2),
        "total_return": round(total_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "equity_history": history
    }
