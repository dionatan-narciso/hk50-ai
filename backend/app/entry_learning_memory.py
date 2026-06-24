import os
import pandas as pd

ENTRY_MEMORY_FILE = "data/entry_learning_memory.csv"


DEFAULT_ENTRY_WEIGHTS = {
    "rsi_rising_bonus": 5,
    "rsi_falling_penalty": -5,
    "negative_candle_penalty": -3,
    "ma20_stretch_bonus": 2,
    "ma50_stretch_bonus": 2,
    "extreme_rsi_penalty": -3,
}


def ensure_entry_memory():
    os.makedirs("data", exist_ok=True)

    if (
        not os.path.exists(ENTRY_MEMORY_FILE)
        or os.path.getsize(ENTRY_MEMORY_FILE) == 0
    ):
        pd.DataFrame([DEFAULT_ENTRY_WEIGHTS]).to_csv(
            ENTRY_MEMORY_FILE,
            index=False
        )


def load_entry_weights():
    ensure_entry_memory()

    try:
        df = pd.read_csv(ENTRY_MEMORY_FILE)
    except Exception:
        pd.DataFrame([DEFAULT_ENTRY_WEIGHTS]).to_csv(
            ENTRY_MEMORY_FILE,
            index=False
        )
        return DEFAULT_ENTRY_WEIGHTS.copy()

    if df.empty:
        return DEFAULT_ENTRY_WEIGHTS.copy()

    latest = df.iloc[-1].to_dict()

    return {
        key: int(latest.get(key, default))
        for key, default in DEFAULT_ENTRY_WEIGHTS.items()
    }


def save_entry_weights(weights):
    os.makedirs("data", exist_ok=True)

    pd.DataFrame([weights]).to_csv(
        ENTRY_MEMORY_FILE,
        index=False
    )


def update_entry_weights_after_replay(win_rate, average_return):
    weights = load_entry_weights()

    decision = "KEEP"

    if win_rate >= 46 and average_return >= 0.13:
        weights["rsi_rising_bonus"] = min(
            weights["rsi_rising_bonus"] + 1,
            8
        )
        weights["extreme_rsi_penalty"] = max(
            weights["extreme_rsi_penalty"] - 1,
            -6
        )
        decision = "STRENGTHEN"

    elif win_rate < 43 or average_return < 0.10:
        weights["rsi_rising_bonus"] = max(
            weights["rsi_rising_bonus"] - 1,
            2
        )
        weights["extreme_rsi_penalty"] = min(
            weights["extreme_rsi_penalty"] + 1,
            -1
        )
        decision = "WEAKEN"

    save_entry_weights(weights)

    return {
        "decision": decision,
        "entry_weights": weights,
        "win_rate": win_rate,
        "average_return": average_return,
    }