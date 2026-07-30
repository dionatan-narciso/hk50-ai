import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def _safe_rate(wins, trades):
    if trades == 0:
        return 0
    return round((wins / trades) * 100, 2)


def analyze_replay_exit_reasons():
    replay_file = resolve_runtime_paths().replay_trade_journal

    if not replay_file.exists():
        return {"status": "no_replay_data"}

    df = pd.read_csv(replay_file)

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
