import csv
import os
from copy import deepcopy
from datetime import datetime

MEMORY_FILE = "data/entry_learning_memory.csv"
TUNING_FILE = "data/entry_weight_tuning_log.csv"


DEFAULT_WEIGHTS = {
    "rsi_rising_bonus": 5,
    "rsi_falling_penalty": -5,
    "negative_candle_penalty": -3,
    "ma20_stretch_bonus": 2,
    "ma50_stretch_bonus": 2,
    "extreme_rsi_penalty": -3,
}


def load_entry_weights():
    if not os.path.exists(MEMORY_FILE):
        return DEFAULT_WEIGHTS.copy()

    with open(MEMORY_FILE, "r", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return DEFAULT_WEIGHTS.copy()

    latest = rows[-1]

    weights = {}
    for key, default_value in DEFAULT_WEIGHTS.items():
        weights[key] = int(float(latest.get(key, default_value)))

    return weights


def save_entry_weights(weights, decision, win_rate, average_return):
    os.makedirs("data", exist_ok=True)

    file_exists = os.path.exists(MEMORY_FILE)

    fieldnames = [
        "timestamp",
        "decision",
        "win_rate",
        "average_return",
        "rsi_rising_bonus",
        "rsi_falling_penalty",
        "negative_candle_penalty",
        "ma20_stretch_bonus",
        "ma50_stretch_bonus",
        "extreme_rsi_penalty",
    ]

    with open(MEMORY_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "win_rate": round(win_rate, 2),
            "average_return": round(average_return, 3),
            **weights,
        })


def log_tuning_result(weight_name, old_value, new_value, decision, base_result, test_result):
    os.makedirs("data", exist_ok=True)

    file_exists = os.path.exists(TUNING_FILE)

    fieldnames = [
        "timestamp",
        "weight_name",
        "old_value",
        "new_value",
        "decision",
        "base_win_rate",
        "test_win_rate",
        "base_average_return",
        "test_average_return",
    ]

    with open(TUNING_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "weight_name": weight_name,
            "old_value": old_value,
            "new_value": new_value,
            "decision": decision,
            "base_win_rate": round(base_result.get("win_rate", 0), 2),
            "test_win_rate": round(test_result.get("win_rate", 0), 2),
            "base_average_return": round(base_result.get("average_return", 0), 3),
            "test_average_return": round(test_result.get("average_return", 0), 3),
        })


def score_result(result):
    win_rate = result.get("win_rate", 0)
    average_return = result.get("average_return", 0)

    return average_return + (win_rate / 100)


def tune_entry_weights(run_replay_function):
    current_weights = load_entry_weights()

    base_result = run_replay_function(entry_weights_override=current_weights)

    best_weights = deepcopy(current_weights)
    best_result = base_result

    tuning_attempts = []

    for weight_name, current_value in current_weights.items():
        for adjustment in [1, -1]:
            test_weights = deepcopy(best_weights)
            test_weights[weight_name] = current_value + adjustment

            test_result = run_replay_function(entry_weights_override=test_weights)

            if score_result(test_result) > score_result(best_result):
                decision = "KEEP"
                best_weights = deepcopy(test_weights)
                best_result = test_result
            else:
                decision = "REJECT"

            log_tuning_result(
                weight_name=weight_name,
                old_value=current_value,
                new_value=test_weights[weight_name],
                decision=decision,
                base_result=best_result,
                test_result=test_result,
            )

            tuning_attempts.append({
                "weight_name": weight_name,
                "old_value": current_value,
                "new_value": test_weights[weight_name],
                "decision": decision,
                "test_win_rate": test_result.get("win_rate", 0),
                "test_average_return": test_result.get("average_return", 0),
            })

    final_decision = "UPDATED" if best_weights != current_weights else "KEEP"

    save_entry_weights(
        weights=best_weights,
        decision=final_decision,
        win_rate=best_result.get("win_rate", 0),
        average_return=best_result.get("average_return", 0),
    )

    return {
        "status": "completed",
        "stage": "Stage 26 - Adaptive Entry Weight Tuning",
        "decision": final_decision,
        "starting_weights": current_weights,
        "final_weights": best_weights,
        "base_result": base_result,
        "best_result": best_result,
        "tuning_attempts": tuning_attempts,
    }