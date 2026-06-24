import os
import pandas as pd
from replay_learning_controller import get_current_learning_strength

REPLAY_MEMORY = "data/replay/replay_learning_memory.csv"


def get_replay_penalty(
    strategy,
    market_regime=None,
    volatility_regime=None,
    rotation_changed=None
):
    if not os.path.exists(REPLAY_MEMORY):
        return {
            "penalty_available": False,
            "total_adjustment": 0,
            "reasons": ["No replay learning memory found."]
        }

    df = pd.read_csv(REPLAY_MEMORY)

    learning_strength = get_current_learning_strength()

    total_adjustment = 0
    reasons = []

    checks = [
        ("strategy", strategy),
        ("strategy+market_regime", f"{strategy} | {market_regime}"),
        ("strategy+volatility_regime", f"{strategy} | {volatility_regime}"),
        ("strategy+rotation_changed", f"{strategy} | {rotation_changed}"),
    ]

    for learning_type, key in checks:
        match = df[
            (df["learning_type"] == learning_type) &
            (df["key"] == str(key))
        ]

        if not match.empty:
            row = match.iloc[0]
            adjustment = int(row["score_adjustment"])

            # Use only the strongest negative penalty instead of stacking all penalties
            if adjustment < total_adjustment:
                total_adjustment = adjustment

            reasons.append(
                f"{learning_type}: {key} adjustment {adjustment} "
                f"(win rate {row['win_rate']}%, avg return {row['average_return']}%)"
            )

    return {
        "penalty_available": True,
        "strategy": strategy,
        "market_regime": market_regime,
        "volatility_regime": volatility_regime,
        "rotation_changed": rotation_changed,
        "total_adjustment": int(total_adjustment * learning_strength),
        "learning_strength": learning_strength,
        "reasons": reasons
    }