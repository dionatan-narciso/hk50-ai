import pandas as pd

from app.runtime_paths import resolve_runtime_paths


def _safe_rate(wins, trades):
    if trades == 0:
        return 0
    return round((wins / trades) * 100, 2)


def _summarise_group(df, group_col):
    if group_col not in df.columns:
        return []

    results = []

    for name, group in df.groupby(group_col):
        trades = len(group)
        wins = len(group[group["return_percent"] > 0])
        losses = len(group[group["return_percent"] <= 0])

        results.append({
            group_col: str(name),
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": _safe_rate(wins, trades),
            "average_return": round(group["return_percent"].mean(), 3),
            "best_trade": round(group["return_percent"].max(), 3),
            "worst_trade": round(group["return_percent"].min(), 3),
        })

    return sorted(results, key=lambda x: x["average_return"], reverse=True)


def get_replay_analytics():
    replay_journal = resolve_runtime_paths().replay_trade_journal

    if not replay_journal.exists():
        return {
            "status": "no_replay_data",
            "message": "No replay trade journal found yet."
        }

    df = pd.read_csv(replay_journal)

    if df.empty:
        return {
            "status": "empty",
            "message": "Replay journal exists but has no trades."
        }

    if "return_percent" not in df.columns:
        return {
            "status": "error",
            "message": "Replay journal must contain return_percent column."
        }

    total_trades = len(df)
    wins = len(df[df["return_percent"] > 0])
    losses = len(df[df["return_percent"] <= 0])

    analytics = {
        "status": "completed",
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": _safe_rate(wins, total_trades),
        "average_return": round(df["return_percent"].mean(), 3),
        "best_trade": round(df["return_percent"].max(), 3),
        "worst_trade": round(df["return_percent"].min(), 3),

        "strategy_summary": _summarise_group(df, "strategy"),
        "market_regime_summary": _summarise_group(df, "market_regime"),
        "volatility_regime_summary": _summarise_group(df, "volatility_regime"),
        "quality_summary": _summarise_group(df, "quality"),
        "rotation_summary": _summarise_group(df, "rotation_changed"),
        "confidence_bucket_summary": _summarise_group(df, "confidence_bucket"),
    }

    return analytics
