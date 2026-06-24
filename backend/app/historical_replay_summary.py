import os
import pandas as pd

REPLAY_TRADES_FILE = "data/replay/replay_trade_journal.csv"


def get_historical_replay_summary():
    if not os.path.exists(REPLAY_TRADES_FILE):
        return {
            "status": "empty",
            "reason": "No replay trades found yet."
        }

    df = pd.read_csv(REPLAY_TRADES_FILE)

    if df.empty:
        return {
            "status": "empty",
            "reason": "Replay trade journal is empty."
        }

    total_trades = len(df)
    wins = len(df[df["return_percent"] > 0])
    losses = len(df[df["return_percent"] <= 0])

    win_rate = round((wins / total_trades) * 100, 2) if total_trades else 0
    average_return = round(df["return_percent"].mean(), 3)
    best_trade = round(df["return_percent"].max(), 3)
    worst_trade = round(df["return_percent"].min(), 3)

    strategy_summary = (
        df.groupby("strategy")
        .agg(
            trades=("strategy", "count"),
            average_return=("return_percent", "mean"),
            best_trade=("return_percent", "max"),
            worst_trade=("return_percent", "min"),
        )
        .reset_index()
    )

    strategy_summary["average_return"] = strategy_summary[
        "average_return"
    ].round(3)

    strategy_summary = strategy_summary.sort_values(
        by="average_return",
        ascending=False
    )

    return {
        "status": "completed",
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "average_return": average_return,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "best_strategy": strategy_summary.iloc[0].to_dict()
        if not strategy_summary.empty
        else None,
        "strategy_summary": strategy_summary.to_dict("records"),
        "note": "Replay summary uses sandbox replay data only."
    }