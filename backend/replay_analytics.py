import os
import pandas as pd

REPLAY_JOURNAL = "data/replay/replay_trade_journal.csv"


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

def _distance_bucket(value):
    try:
        if value is None or str(value) == "nan":
            return "UNKNOWN"

        value = float(value)

        if value <= 0.25:
            return "0-0.25%"
        elif value <= 0.50:
            return "0.25-0.50%"
        elif value <= 1.00:
            return "0.50-1.00%"
        elif value <= 2.00:
            return "1.00-2.00%"
        else:
            return "2.00%+"

    except Exception:
        return "UNKNOWN"


def _add_support_resistance_buckets(df):
    if "distance_to_support" in df.columns:
        df["distance_to_support_bucket"] = df["distance_to_support"].apply(
            _distance_bucket
        )

    if "distance_to_resistance" in df.columns:
        df["distance_to_resistance_bucket"] = df[
            "distance_to_resistance"
        ].apply(_distance_bucket)

    return df

def get_replay_analytics():
    if not os.path.exists(REPLAY_JOURNAL):
        return {
            "status": "no_replay_data",
            "message": "No replay trade journal found yet."
        }

    df = pd.read_csv(REPLAY_JOURNAL)
    df = _add_support_resistance_buckets(df)

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

        "support_resistance_summary": _summarise_group(
            df,
            "support_resistance_status"
        ),
        "distance_to_support_bucket_summary": _summarise_group(
            df,
            "distance_to_support_bucket"
        ),
        "distance_to_resistance_bucket_summary": _summarise_group(
            df,
            "distance_to_resistance_bucket"
        ),
        "support_strength_summary": _summarise_group(
            df,
            "support_strength"
        ),
        "resistance_strength_summary": _summarise_group(
            df,
            "resistance_strength"
        ),
    }

    return analytics