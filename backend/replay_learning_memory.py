import os
import pandas as pd

REPLAY_JOURNAL = "data/replay/replay_trade_journal.csv"
REPLAY_MEMORY = "data/replay/replay_learning_memory.csv"


def _safe_rate(wins, trades):
    if trades == 0:
        return 0
    return round((wins / trades) * 100, 2)


def _score_from_performance(win_rate, avg_return, trades):
    if trades < 10:
        return 0

    score = 0

    if win_rate < 35:
        score -= 10
    elif win_rate < 45:
        score -= 5
    elif win_rate > 65:
        score += 10
    elif win_rate > 55:
        score += 5

    if avg_return < 0:
        score -= 5
    elif avg_return > 0.30:
        score += 10
    elif avg_return > 0.15:
        score += 5

    return score


def build_replay_learning_memory():
    if not os.path.exists(REPLAY_JOURNAL):
        return {"status": "no_replay_data"}

    df = pd.read_csv(REPLAY_JOURNAL)

    if df.empty:
        return {"status": "empty"}

    rows = []

    groups = [
        ["strategy"],
        ["strategy", "market_regime"],
        ["strategy", "volatility_regime"],
        ["strategy", "rotation_changed"],
    ]

    for group_cols in groups:
        missing = [col for col in group_cols if col not in df.columns]
        if missing:
            continue

        for key, group in df.groupby(group_cols):
            trades = len(group)
            wins = len(group[group["return_percent"] > 0])
            losses = len(group[group["return_percent"] <= 0])
            win_rate = _safe_rate(wins, trades)
            avg_return = round(group["return_percent"].mean(), 3)
            score_adjustment = _score_from_performance(win_rate, avg_return, trades)

            if not isinstance(key, tuple):
                key = (key,)

            rows.append({
                "learning_type": "+".join(group_cols),
                "key": " | ".join([str(x) for x in key]),
                "trades": trades,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "average_return": avg_return,
                "score_adjustment": score_adjustment,
            })

    memory_df = pd.DataFrame(rows)
    os.makedirs("data/replay", exist_ok=True)
    memory_df.to_csv(REPLAY_MEMORY, index=False)

    return {
        "status": "completed",
        "memory_file": REPLAY_MEMORY,
        "rows_created": len(memory_df),
        "learning_memory": rows,
    }