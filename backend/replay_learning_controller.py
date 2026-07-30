from datetime import datetime

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def _control_file():
    """Resolve replay controller state at call time for test/deployment isolation."""

    return resolve_runtime_paths().replay_learning_control


def ensure_control_folder():
    _control_file().parent.mkdir(parents=True, exist_ok=True)


def load_control_history():
    control_file = _control_file()

    if not control_file.exists():
        return pd.DataFrame()

    return pd.read_csv(control_file)


def get_current_learning_strength():
    history = load_control_history()

    if history.empty or "learning_strength" not in history.columns:
        return 1.0

    return float(history.iloc[-1]["learning_strength"])


def decide_next_learning_strength(
    total_trades,
    blocked_by_learning,
    win_rate,
    average_return
):
    current_strength = get_current_learning_strength()

    total_candidates = total_trades + blocked_by_learning

    if total_candidates == 0:
        blocked_rate = 0
    else:
        blocked_rate = round((blocked_by_learning / total_candidates) * 100, 2)

    decision = "KEEP"

    new_strength = current_strength

    if blocked_rate > 80:
        new_strength = max(0.25, current_strength - 0.25)
        decision = "REDUCE_LEARNING_STRENGTH_TOO_STRICT"

    elif blocked_rate < 10 and win_rate < 45:
        new_strength = min(2.0, current_strength + 0.25)
        decision = "INCREASE_LEARNING_STRENGTH_TOO_SOFT"

    elif average_return > 0.15 and win_rate >= 45:
        decision = "KEEP_WORKING_CONFIGURATION"

    new_strength = round(new_strength, 2)

    return {
        "current_strength": current_strength,
        "new_strength": new_strength,
        "blocked_rate": blocked_rate,
        "decision": decision,
    }


def record_replay_control_result(
    total_trades,
    blocked_by_learning,
    win_rate,
    average_return
):
    ensure_control_folder()

    control = decide_next_learning_strength(
        total_trades=total_trades,
        blocked_by_learning=blocked_by_learning,
        win_rate=win_rate,
        average_return=average_return,
    )

    row = {
        "timestamp": datetime.now().isoformat(),
        "total_trades": total_trades,
        "blocked_by_learning": blocked_by_learning,
        "blocked_rate": control["blocked_rate"],
        "win_rate": win_rate,
        "average_return": average_return,
        "previous_learning_strength": control["current_strength"],
        "learning_strength": control["new_strength"],
        "decision": control["decision"],
    }

    history = load_control_history()
    history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
    history.to_csv(_control_file(), index=False)

    return row
