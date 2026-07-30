import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def analyze_replay_exits():
    replay_file = resolve_runtime_paths().replay_trade_journal

    if not replay_file.exists():
        return {"status": "no_replay_data"}

    df = pd.read_csv(replay_file)

    if df.empty:
        return {"status": "empty_replay"}

    if "return_percent" not in df.columns:
        return {
            "status": "error",
            "message": "Replay file must contain return_percent column."
        }

    winners = df[df["return_percent"] > 0]
    losers = df[df["return_percent"] <= 0]

    total_wins = winners["return_percent"].sum()
    total_losses = abs(losers["return_percent"].sum())

    return {
        "status": "completed",
        "total_trades": len(df),
        "wins": len(winners),
        "losses": len(losers),
        "avg_win": round(winners["return_percent"].mean(), 3) if len(winners) else 0,
        "avg_loss": round(losers["return_percent"].mean(), 3) if len(losers) else 0,
        "best_trade": round(df["return_percent"].max(), 3),
        "worst_trade": round(df["return_percent"].min(), 3),
        "profit_factor": round(total_wins / total_losses, 2) if total_losses else 0,
    }
