from datetime import datetime
import os

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def get_paper_trade_journal_path():
    return resolve_runtime_paths().paper_trade_journal


def save_trade_journal_entry(
    strategy,
    direction,
    entry_price,
    exit_price,
    notes="",
    confidence=None,
    vote_signal=None,
    vote_strength=None,
    total_votes=None,
    raw_signal=None,
    final_signal=None,
    result=None,
):
    file_path = get_paper_trade_journal_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)

    trade = {
        "timestamp": timestamp,
        "strategy": strategy,
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "result_pct": result_pct,
        "result": result or ("WIN" if result_pct > 0 else "LOSS"),
        "confidence": confidence,
        "vote_signal": vote_signal,
        "vote_strength": vote_strength,
        "total_votes": total_votes,
        "raw_signal": raw_signal,
        "final_signal": final_signal,
        "notes": notes,
    }

    new_row = pd.DataFrame([trade])

    if file_path.exists():
        existing = pd.read_csv(file_path)

        for column in trade.keys():
            if column not in existing.columns:
                existing[column] = ""

        existing = pd.concat([existing, new_row], ignore_index=True)
        existing.to_csv(file_path, index=False)
    else:
        new_row.to_csv(file_path, index=False)

    return trade


def run_trade_journal():
    file_path = get_paper_trade_journal_path()

    if not file_path.exists():
        return {
            "total_trades": 0,
            "win_rate": 0,
            "average_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "trades": [],
        }

    df = pd.read_csv(file_path)

    if df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "average_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "trades": [],
        }

    wins = df[df["result_pct"] > 0]

    return {
        "total_trades": int(len(df)),
        "win_rate": round((len(wins) / len(df)) * 100, 2),
        "average_return": round(float(df["result_pct"].mean()), 2),
        "best_trade": round(float(df["result_pct"].max()), 2),
        "worst_trade": round(float(df["result_pct"].min()), 2),
        "trades": df.tail(10).to_dict(orient="records"),
    }


def run_live_learning_feed():
    from app.research_engine import run_research_director

    trade_data = run_trade_journal()
    director = run_research_director()

    feed = []
    best_strategy = director.get("best_strategy")
    most_robust = director.get("most_robust")

    if best_strategy:
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Research",
            "signal": "BUY" if best_strategy["return"] >= 0 else "SELL",
            "strategy": best_strategy["strategy"],
            "result": f"{best_strategy['return']}%",
            "confidence": f"{director.get('confidence_score', 0)}%",
        })

    if most_robust:
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Walk Forward",
            "signal": most_robust["robustness"],
            "strategy": most_robust["strategy"],
            "result": f"{most_robust['test_return']}%",
            "confidence": f"{most_robust['robustness_score']}%",
        })

    for trade in trade_data.get("trades", [])[-5:]:
        feed.append({
            "time": str(trade.get("timestamp", ""))[-8:],
            "source": "Paper Trade",
            "signal": trade.get("direction", "LONG"),
            "strategy": trade.get("strategy", ""),
            "result": f"{trade.get('result_pct', 0)}%",
            "confidence": "Tracked",
        })

    return {"feed": feed[:8]}
