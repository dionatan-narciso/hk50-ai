import os
import csv

VOTING_MEMORY_FILE = "backend/data/voting_performance_memory.csv"


def ensure_voting_memory_file():
    os.makedirs(os.path.dirname(VOTING_MEMORY_FILE), exist_ok=True)

    if not os.path.exists(VOTING_MEMORY_FILE):
        with open(VOTING_MEMORY_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "vote_signal",
                "vote_strength",
                "total_votes",
                "strategy_signal",
                "final_signal",
                "trade_result",
                "won"
            ])


def save_voting_result(
    vote_signal,
    vote_strength,
    total_votes,
    strategy_signal,
    final_signal,
    trade_result
):
    ensure_voting_memory_file()

    won = trade_result > 0

    with open(VOTING_MEMORY_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            vote_signal,
            vote_strength,
            total_votes,
            strategy_signal,
            final_signal,
            trade_result,
            won
        ])


def load_voting_performance_memory():
    ensure_voting_memory_file()

    rows = []

    with open(VOTING_MEMORY_FILE, "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                rows.append({
                    "vote_signal": row["vote_signal"],
                    "vote_strength": int(row["vote_strength"]),
                    "total_votes": int(row["total_votes"]),
                    "strategy_signal": row["strategy_signal"],
                    "final_signal": row["final_signal"],
                    "trade_result": float(row["trade_result"]),
                    "won": row["won"] == "True",
                })
            except Exception:
                continue

    return rows


def summarise_voting_performance():
    rows = load_voting_performance_memory()

    if not rows:
        return {
            "total_records": 0,
            "summary": [],
            "best_vote_strength": None,
            "best_win_rate": 0,
        }

    grouped = {}

    for row in rows:
        strength = row["vote_strength"]

        if strength not in grouped:
            grouped[strength] = {
                "vote_strength": strength,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_return": 0,
            }

        grouped[strength]["total_trades"] += 1
        grouped[strength]["total_return"] += row["trade_result"]

        if row["won"]:
            grouped[strength]["wins"] += 1
        else:
            grouped[strength]["losses"] += 1

    summary = []

    for strength, data in grouped.items():
        total = data["total_trades"]
        wins = data["wins"]

        win_rate = round((wins / total) * 100, 2) if total else 0
        average_return = round(data["total_return"] / total, 2) if total else 0

        summary.append({
            "vote_strength": strength,
            "total_trades": total,
            "wins": wins,
            "losses": data["losses"],
            "win_rate": win_rate,
            "average_return": average_return,
        })

    summary = sorted(summary, key=lambda x: x["vote_strength"], reverse=True)

    best = max(summary, key=lambda x: x["win_rate"]) if summary else None

    return {
        "total_records": len(rows),
        "summary": summary,
        "best_vote_strength": best["vote_strength"] if best else None,
        "best_win_rate": best["win_rate"] if best else 0,
    }

def get_vote_strength_win_rate(vote_strength):
    memory = summarise_voting_performance()

    for row in memory.get("summary", []):
        if row.get("vote_strength") == vote_strength:
            return row.get("win_rate", 0)

    return None