import csv

from app.runtime_paths import resolve_runtime_paths


QUALITY_MEMORY_FIELDS = [
    "quality",
    "total_trades",
    "wins",
    "losses",
    "avg_return",
    "best_return",
    "worst_return",
]


def get_quality_memory_file():
    return resolve_runtime_paths().paper_quality_performance_memory


def ensure_quality_memory_file():
    quality_memory_file = get_quality_memory_file()
    quality_memory_file.parent.mkdir(parents=True, exist_ok=True)

    if not quality_memory_file.exists():
        with quality_memory_file.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(QUALITY_MEMORY_FIELDS)


def update_quality_performance_memory(quality, trade_return):
    ensure_quality_memory_file()
    quality_memory_file = get_quality_memory_file()

    with quality_memory_file.open("r", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    found = False

    for row in rows:
        if row["quality"] == quality:
            total_trades = int(row["total_trades"]) + 1
            wins = int(row["wins"]) + (1 if trade_return > 0 else 0)
            losses = int(row["losses"]) + (1 if trade_return <= 0 else 0)

            old_avg = float(row["avg_return"])
            avg_return = ((old_avg * (total_trades - 1)) + trade_return) / total_trades

            best_return = max(float(row["best_return"]), trade_return)
            worst_return = min(float(row["worst_return"]), trade_return)

            row["total_trades"] = total_trades
            row["wins"] = wins
            row["losses"] = losses
            row["avg_return"] = round(avg_return, 3)
            row["best_return"] = round(best_return, 3)
            row["worst_return"] = round(worst_return, 3)

            found = True
            break

    if not found:
        rows.append({
            "quality": quality,
            "total_trades": 1,
            "wins": 1 if trade_return > 0 else 0,
            "losses": 1 if trade_return <= 0 else 0,
            "avg_return": round(trade_return, 3),
            "best_return": round(trade_return, 3),
            "worst_return": round(trade_return, 3)
        })

    with quality_memory_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=QUALITY_MEMORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def get_quality_performance_summary():
    ensure_quality_memory_file()
    quality_memory_file = get_quality_memory_file()

    with quality_memory_file.open("r", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        return {
            "status": "empty",
            "message": "No quality performance data yet"
        }

    for row in rows:
        total = int(row["total_trades"])
        wins = int(row["wins"])
        row["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0

    best_quality = max(rows, key=lambda x: float(x["avg_return"]))

    return {
        "status": "ready",
        "quality_rows": rows,
        "best_quality": best_quality["quality"],
        "best_quality_avg_return": float(best_quality["avg_return"])
    }


def get_quality_analytics_bonus(quality):
    summary = get_quality_performance_summary()

    if summary.get("status") != "ready":
        return {
            "quality": quality,
            "analytics_bonus": 0,
            "reason": "Not enough quality performance data yet"
        }

    rows = summary.get("quality_rows", [])

    matching_row = None

    for row in rows:
        if row.get("quality") == quality:
            matching_row = row
            break

    if matching_row is None:
        return {
            "quality": quality,
            "analytics_bonus": 0,
            "reason": "No historical trades for this quality level yet"
        }

    total_trades = int(matching_row.get("total_trades", 0))
    win_rate = float(matching_row.get("win_rate", 0))
    avg_return = float(matching_row.get("avg_return", 0))

    if total_trades < 3:
        return {
            "quality": quality,
            "analytics_bonus": 0,
            "reason": "Not enough trades for this quality level yet"
        }

    analytics_bonus = 0
    reason = "Neutral quality performance"

    if win_rate >= 70 and avg_return > 0:
        analytics_bonus = 5
        reason = "Quality level has strong historical performance"
    elif win_rate >= 55 and avg_return > 0:
        analytics_bonus = 2
        reason = "Quality level has positive historical performance"
    elif win_rate <= 40 or avg_return < 0:
        analytics_bonus = -5
        reason = "Quality level has weak historical performance"

    return {
        "quality": quality,
        "analytics_bonus": analytics_bonus,
        "reason": reason,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_return": avg_return
    }
