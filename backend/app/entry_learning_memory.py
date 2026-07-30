import os
from pathlib import Path

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


# Legacy paper path remains the default for live/paper callers in Batch 1B.
# Migrating paper state requires a separate, explicit compatibility batch.
ENTRY_MEMORY_FILE = Path("data/entry_learning_memory.csv")


DEFAULT_ENTRY_WEIGHTS = {
    "rsi_rising_bonus": 5,
    "rsi_falling_penalty": -5,
    "negative_candle_penalty": -3,
    "ma20_stretch_bonus": 2,
    "ma50_stretch_bonus": 2,
    "extreme_rsi_penalty": -3,
}


def _normalize_memory_file(memory_file=None):
    return Path(memory_file) if memory_file is not None else ENTRY_MEMORY_FILE


def ensure_entry_memory(memory_file=None):
    target = _normalize_memory_file(memory_file)
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists() or target.stat().st_size == 0:
        pd.DataFrame([DEFAULT_ENTRY_WEIGHTS]).to_csv(target, index=False)

    return target


def load_entry_weights(memory_file=None):
    target = ensure_entry_memory(memory_file)

    try:
        df = pd.read_csv(target)
    except Exception:
        pd.DataFrame([DEFAULT_ENTRY_WEIGHTS]).to_csv(target, index=False)
        return DEFAULT_ENTRY_WEIGHTS.copy()

    if df.empty:
        return DEFAULT_ENTRY_WEIGHTS.copy()

    latest = df.iloc[-1].to_dict()

    return {
        key: int(latest.get(key, default))
        for key, default in DEFAULT_ENTRY_WEIGHTS.items()
    }


def save_entry_weights(weights, memory_file=None):
    target = _normalize_memory_file(memory_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([weights]).to_csv(target, index=False)


def update_entry_weights_after_replay(win_rate, average_return, memory_file=None):
    """Update replay-local entry weights without touching paper state."""

    target = (
        Path(memory_file)
        if memory_file is not None
        else resolve_runtime_paths().replay_entry_learning_memory
    )
    weights = load_entry_weights(target)

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

    save_entry_weights(weights, target)

    return {
        "decision": decision,
        "entry_weights": weights,
        "win_rate": win_rate,
        "average_return": average_return,
        "memory_file": str(target),
    }
