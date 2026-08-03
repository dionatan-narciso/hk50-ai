import pandas as pd

from app.runtime_paths import resolve_runtime_paths


COLUMNS = [
    "strategy",
    "wins",
    "losses",
    "total_trades",
    "win_rate",
    "average_return",
]


def get_strategy_performance_path():
    return resolve_runtime_paths().paper_strategy_performance_memory


def ensure_performance_file():
    performance_file = get_strategy_performance_path()
    performance_file.parent.mkdir(parents=True, exist_ok=True)

    if not performance_file.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(performance_file, index=False)

    return performance_file


def load_live_strategy_performance():
    performance_file = ensure_performance_file()
    return pd.read_csv(performance_file)


def get_live_performance_memory_response():
    """Return the API response shape using canonical paper strategy memory."""
    try:
        return {
            "strategies": load_live_strategy_performance().to_dict("records")
        }
    except Exception:
        return {
            "strategies": []
        }


def update_live_strategy_memory(strategy_name, trade_return):
    performance_file = ensure_performance_file()
    df = pd.read_csv(performance_file)

    existing = df[df["strategy"] == strategy_name]

    if existing.empty:
        wins = 1 if trade_return > 0 else 0
        losses = 1 if trade_return <= 0 else 0

        new_row = {
            "strategy": strategy_name,
            "wins": wins,
            "losses": losses,
            "total_trades": 1,
            "win_rate": 100 if wins else 0,
            "average_return": trade_return,
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    else:
        idx = existing.index[0]

        wins = int(df.loc[idx, "wins"])
        losses = int(df.loc[idx, "losses"])
        total = int(df.loc[idx, "total_trades"])
        avg_return = float(df.loc[idx, "average_return"])

        if trade_return > 0:
            wins += 1
        else:
            losses += 1

        total += 1
        avg_return = ((avg_return * (total - 1)) + trade_return) / total

        df.loc[idx, "wins"] = wins
        df.loc[idx, "losses"] = losses
        df.loc[idx, "total_trades"] = total
        df.loc[idx, "win_rate"] = round((wins / total) * 100, 2)
        df.loc[idx, "average_return"] = round(avg_return, 3)

    df.to_csv(performance_file, index=False)


def summarise_live_strategy_performance():
    df = load_live_strategy_performance()

    if df.empty:
        return {
            "total_strategies": 0,
            "strategies": [],
            "best_live_strategy": None,
            "best_live_score": 0,
        }

    strategies = []

    for _, row in df.iterrows():
        strategy = row["strategy"]
        total_trades = int(row["total_trades"])
        win_rate = float(row["win_rate"])
        average_return = float(row["average_return"])

        trade_count_score = min(total_trades * 5, 25)
        win_rate_score = win_rate * 0.5
        return_score = max(min(average_return * 10, 25), -25)

        live_score = round(
            trade_count_score + win_rate_score + return_score,
            2,
        )

        strategies.append({
            "strategy": strategy,
            "wins": int(row["wins"]),
            "losses": int(row["losses"]),
            "total_trades": total_trades,
            "win_rate": win_rate,
            "average_return": average_return,
            "live_score": live_score,
        })

    strategies = sorted(
        strategies,
        key=lambda x: x["live_score"],
        reverse=True,
    )

    best = strategies[0] if strategies else None

    return {
        "total_strategies": len(strategies),
        "strategies": strategies,
        "best_live_strategy": best["strategy"] if best else None,
        "best_live_score": best["live_score"] if best else 0,
    }


def get_strategy_performance_bonus(strategy_name):
    summary = summarise_live_strategy_performance()
    strategies = summary.get("strategies", [])

    for strategy in strategies:
        if strategy.get("strategy") == strategy_name:
            total_trades = int(strategy.get("total_trades", 0))
            win_rate = float(strategy.get("win_rate", 0))
            average_return = float(strategy.get("average_return", 0))
            live_score = float(strategy.get("live_score", 0))

            if total_trades < 3:
                return {
                    "strategy": strategy_name,
                    "strategy_performance_bonus": 0,
                    "reason": "Not enough live trades for this strategy yet",
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                    "average_return": average_return,
                    "live_score": live_score,
                }

            bonus = 0
            reason = "Neutral live strategy performance"

            if live_score >= 70 and win_rate >= 60 and average_return > 0:
                bonus = 8
                reason = "Strong live strategy performance"
            elif live_score >= 55 and win_rate >= 55 and average_return > 0:
                bonus = 5
                reason = "Positive live strategy performance"
            elif live_score <= 35 or win_rate <= 40 or average_return < 0:
                bonus = -8
                reason = "Weak live strategy performance"

            return {
                "strategy": strategy_name,
                "strategy_performance_bonus": bonus,
                "reason": reason,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "average_return": average_return,
                "live_score": live_score,
            }

    return {
        "strategy": strategy_name,
        "strategy_performance_bonus": 0,
        "reason": "No live performance data for this strategy yet",
        "total_trades": 0,
        "win_rate": 0,
        "average_return": 0,
        "live_score": 0,
    }
