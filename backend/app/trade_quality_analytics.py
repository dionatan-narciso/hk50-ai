import os
import pandas as pd

REPLAY_TRADES_FILE = "data/replay/replay_trade_journal.csv"


def get_trade_quality_analytics():
    if not os.path.exists(REPLAY_TRADES_FILE):
        return {
            "status": "no_data",
            "reason": "Replay trade journal not found."
        }

    df = pd.read_csv(REPLAY_TRADES_FILE)

    if df.empty:
        return {
            "status": "no_data",
            "reason": "Replay trade journal is empty."
        }

    required_columns = ["return_percent", "trade_quality_score", "trade_quality_label"]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        return {
            "status": "missing_columns",
            "missing_columns": missing_columns,
            "reason": "Run historical replay again after Stage 27 quality scoring."
        }

    df["return_percent"] = pd.to_numeric(df["return_percent"], errors="coerce")
    df["trade_quality_score"] = pd.to_numeric(
        df["trade_quality_score"],
        errors="coerce"
    )

    df = df.dropna(subset=["return_percent", "trade_quality_score"])

    total_trades = len(df)
    wins = len(df[df["return_percent"] > 0])
    losses = len(df[df["return_percent"] <= 0])

    overall_win_rate = round((wins / total_trades) * 100, 2) if total_trades else 0
    overall_average_return = round(df["return_percent"].mean(), 3) if total_trades else 0

    label_summary = []

    for label, group in df.groupby("trade_quality_label"):
        trades = len(group)
        group_wins = len(group[group["return_percent"] > 0])
        group_losses = len(group[group["return_percent"] <= 0])
        win_rate = round((group_wins / trades) * 100, 2) if trades else 0
        average_return = round(group["return_percent"].mean(), 3) if trades else 0
        best_trade = round(group["return_percent"].max(), 3) if trades else 0
        worst_trade = round(group["return_percent"].min(), 3) if trades else 0
        average_quality_score = round(group["trade_quality_score"].mean(), 2)

        label_summary.append({
            "quality_label": label,
            "trades": trades,
            "wins": group_wins,
            "losses": group_losses,
            "win_rate": win_rate,
            "average_return": average_return,
            "average_quality_score": average_quality_score,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        })

    label_summary = sorted(
        label_summary,
        key=lambda item: item["average_quality_score"],
        reverse=True
    )

    threshold_summary = []

    for threshold in [40, 45, 50, 55, 60, 65, 70, 75, 80]:
        filtered = df[df["trade_quality_score"] >= threshold]
        trades = len(filtered)

        if trades == 0:
            threshold_summary.append({
                "threshold": threshold,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "average_return": 0,
            })
            continue

        filtered_wins = len(filtered[filtered["return_percent"] > 0])
        filtered_losses = len(filtered[filtered["return_percent"] <= 0])

        threshold_summary.append({
            "threshold": threshold,
            "trades": trades,
            "wins": filtered_wins,
            "losses": filtered_losses,
            "win_rate": round((filtered_wins / trades) * 100, 2),
            "average_return": round(filtered["return_percent"].mean(), 3),
        })

    winners = df[df["return_percent"] > 0]
    losers = df[df["return_percent"] <= 0]

    return {
        "status": "completed",
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "overall_win_rate": overall_win_rate,
        "overall_average_return": overall_average_return,
        "winner_average_quality_score": round(
            winners["trade_quality_score"].mean(),
            2
        ) if not winners.empty else 0,
        "loser_average_quality_score": round(
            losers["trade_quality_score"].mean(),
            2
        ) if not losers.empty else 0,
        "quality_label_summary": label_summary,
        "quality_threshold_summary": threshold_summary,
    }