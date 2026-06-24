import os
import pandas as pd

REPLAY_FILE = "data/replay/replay_trade_journal.csv"


def _safe_rate(wins, trades):
    if trades == 0:
        return 0
    return round((wins / trades) * 100, 2)


def analyze_replay_exit_reasons():
    if not os.path.exists(REPLAY_FILE):
        return {"status": "no_replay_data"}

    df = pd.read_csv(REPLAY_FILE)

    if df.empty:
        return {"status": "empty_replay"}

    if "return_percent" not in df.columns:
        return {
            "status": "error",
            "message": "Missing return_percent column."
        }

    if "result" not in df.columns:
        return {
            "status": "error",
            "message": "Missing result column."
        }

    rows = []

    for result, group in df.groupby("result"):
        trades = len(group)
        wins = len(group[group["return_percent"] > 0])
        losses = len(group[group["return_percent"] <= 0])

        rows.append({
            "exit_reason": result,
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": _safe_rate(wins, trades),
            "average_return": round(group["return_percent"].mean(), 3),
            "best_trade": round(group["return_percent"].max(), 3),
            "worst_trade": round(group["return_percent"].min(), 3),
        })

    return {
        "status": "completed",
        "total_trades": len(df),
        "exit_reason_summary": sorted(
            rows,
            key=lambda x: x["average_return"],
            reverse=True
        )
    }