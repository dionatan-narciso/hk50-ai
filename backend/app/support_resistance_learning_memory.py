import os
import pandas as pd

REPLAY_JOURNAL = "data/replay/replay_trade_journal.csv"
SR_MEMORY_FILE = "data/support_resistance_learning.csv"


def safe_rate(wins, trades):
    if trades == 0:
        return 0
    return round((wins / trades) * 100, 2)


def calculate_weight(trades, win_rate, avg_return):
    if trades < 3:
        return 0

    if win_rate >= 70 and avg_return > 0.4:
        return 4
    if win_rate >= 60 and avg_return > 0.2:
        return 3
    if win_rate >= 55 and avg_return > 0:
        return 2
    if win_rate <= 35 or avg_return < -0.25:
        return -4
    if win_rate <= 45 or avg_return < 0:
        return -2

    return 0


def summarise_condition(df, condition_name, condition_value):
    group = df[df[condition_name] == condition_value]

    trades = len(group)

    if trades == 0:
        return None

    wins = len(group[group["return_percent"] > 0])
    losses = len(group[group["return_percent"] <= 0])
    win_rate = safe_rate(wins, trades)
    avg_return = round(group["return_percent"].mean(), 3)

    weight = calculate_weight(
        trades=trades,
        win_rate=win_rate,
        avg_return=avg_return
    )

    return {
        "condition_type": condition_name,
        "condition_value": str(condition_value),
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "learned_weight": weight,
    }


def build_support_resistance_learning_memory():
    if not os.path.exists(REPLAY_JOURNAL):
        return {
            "status": "no_replay_data",
            "message": "Replay journal not found."
        }

    df = pd.read_csv(REPLAY_JOURNAL)

    if df.empty:
        return {
            "status": "empty",
            "message": "Replay journal is empty."
        }

    if "return_percent" not in df.columns:
        return {
            "status": "error",
            "message": "Replay journal must contain return_percent."
        }

    rows = []

    condition_columns = [
        "support_resistance_status",
        "distance_to_support_bucket",
        "distance_to_resistance_bucket",
        "support_strength",
        "resistance_strength",
        "support_resistance_adjustment",
    ]

    for column in condition_columns:
        if column not in df.columns:
            continue

        for value in sorted(df[column].dropna().unique()):
            summary = summarise_condition(df, column, value)
            if summary:
                rows.append(summary)

    os.makedirs("data", exist_ok=True)

    memory_df = pd.DataFrame(rows)
    memory_df.to_csv(SR_MEMORY_FILE, index=False)

    return {
        "status": "completed",
        "memory_file": SR_MEMORY_FILE,
        "conditions_learned": len(rows),
        "strong_positive": [
            row for row in rows
            if row["learned_weight"] >= 3
        ],
        "strong_negative": [
            row for row in rows
            if row["learned_weight"] <= -3
        ],
        "all_conditions": rows,
    }


def load_support_resistance_learning_memory():
    if not os.path.exists(SR_MEMORY_FILE):
        return []

    df = pd.read_csv(SR_MEMORY_FILE)

    if df.empty:
        return []

    return df.to_dict("records")


def get_learned_sr_weight(condition_type, condition_value):
    rows = load_support_resistance_learning_memory()

    for row in rows:
        if (
            str(row.get("condition_type")) == str(condition_type)
            and str(row.get("condition_value")) == str(condition_value)
        ):
            return int(row.get("learned_weight", 0))

    return 0