"""Canonical paper-trade journal access.

The repository accepts both the tracker closed-trade schema and the older
research journal schema. Rows are normalised to expose both naming conventions
so analytics, risk controls and API summaries share one configured file.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def get_paper_trade_journal_path() -> Path:
    return resolve_runtime_paths().paper_trade_journal


def _first_value(trade: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = trade.get(key)
        if value is not None:
            return value
    return default


def normalise_paper_trade(trade: Mapping[str, Any]) -> dict[str, Any]:
    """Return one row compatible with both existing journal schemas."""
    closed_at = _first_value(
        trade,
        "closed_at",
        "timestamp",
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    trade_return = float(_first_value(trade, "return_percent", "result_pct", default=0))
    strategy = _first_value(trade, "strategy", "reason", default="Unknown Strategy")
    direction = _first_value(trade, "direction", "signal", default="UNKNOWN")

    row = dict(trade)
    row.update({
        "timestamp": closed_at,
        "closed_at": closed_at,
        "strategy": strategy,
        "reason": _first_value(trade, "reason", "strategy", default=strategy),
        "direction": direction,
        "signal": _first_value(trade, "signal", "direction", default=direction),
        "result_pct": trade_return,
        "return_percent": trade_return,
    })
    return row


def append_paper_trade(trade: Mapping[str, Any]) -> dict[str, Any]:
    """Append one normalised trade to the configured paper journal."""
    journal_path = get_paper_trade_journal_path()
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    row = normalise_paper_trade(trade)
    new_row = pd.DataFrame([row])

    if journal_path.exists():
        existing = pd.read_csv(journal_path)
        all_columns = list(dict.fromkeys([*existing.columns, *new_row.columns]))
        existing = existing.reindex(columns=all_columns)
        new_row = new_row.reindex(columns=all_columns)
        combined = pd.concat([existing, new_row], ignore_index=True)
        combined.to_csv(journal_path, index=False)
    else:
        new_row.to_csv(journal_path, index=False)

    return row


def load_paper_trade_journal() -> pd.DataFrame:
    journal_path = get_paper_trade_journal_path()
    if not journal_path.exists():
        return pd.DataFrame()
    return pd.read_csv(journal_path)


def save_trade_journal_entry(
    strategy: str,
    direction: str,
    entry_price: float,
    exit_price: float,
    notes: str = "",
    confidence: float | None = None,
    vote_signal: str | None = None,
    vote_strength: int | None = None,
    total_votes: int | None = None,
    raw_signal: str | None = None,
    final_signal: str | None = None,
    result: str | None = None,
) -> dict[str, Any]:
    """Save a manually supplied paper trade using the legacy API contract."""
    entry = float(entry_price)
    exit_value = float(exit_price)
    result_pct = round(((exit_value - entry) / entry) * 100, 2)

    return append_paper_trade({
        "strategy": strategy,
        "direction": direction,
        "entry_price": entry,
        "exit_price": exit_value,
        "result_pct": result_pct,
        "result": result or ("WIN" if result_pct > 0 else "LOSS"),
        "confidence": confidence,
        "vote_signal": vote_signal,
        "vote_strength": vote_strength,
        "total_votes": total_votes,
        "raw_signal": raw_signal,
        "final_signal": final_signal,
        "notes": notes,
    })


def run_trade_journal() -> dict[str, Any]:
    """Return the existing paper-journal summary response shape."""
    df = load_paper_trade_journal()
    if df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "average_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "trades": [],
        }

    returns = pd.to_numeric(df["result_pct"], errors="coerce").fillna(0)
    wins = returns[returns > 0]

    return {
        "total_trades": int(len(df)),
        "win_rate": round((len(wins) / len(df)) * 100, 2),
        "average_return": round(float(returns.mean()), 2),
        "best_trade": round(float(returns.max()), 2),
        "worst_trade": round(float(returns.min()), 2),
        "trades": df.tail(10).to_dict(orient="records"),
    }


def run_live_learning_feed(
    research_director: Callable[[], Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build the existing learning-feed response from the canonical journal."""
    trade_data = run_trade_journal()
    director = research_director()
    feed: list[dict[str, Any]] = []

    best_strategy = director.get("best_strategy")
    most_robust = director.get("most_robust")

    if isinstance(best_strategy, Mapping):
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Research",
            "signal": "BUY" if float(best_strategy.get("return", 0)) >= 0 else "SELL",
            "strategy": best_strategy.get("strategy", ""),
            "result": f"{best_strategy.get('return', 0)}%",
            "confidence": f"{director.get('confidence_score', 0)}%",
        })

    if isinstance(most_robust, Mapping):
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Walk Forward",
            "signal": most_robust.get("robustness", "UNKNOWN"),
            "strategy": most_robust.get("strategy", ""),
            "result": f"{most_robust.get('test_return', 0)}%",
            "confidence": f"{most_robust.get('robustness_score', 0)}%",
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
