import pandas as pd

from app.replay_journal_repository import get_replay_journal_path


def average(values):
    values = pd.to_numeric(pd.Series(values), errors="coerce").dropna().tolist()

    if len(values) == 0:
        return 0

    return round(sum(values) / len(values), 3)


def count_values(series):
    series = series.dropna()
    counts = series.value_counts()

    return {
        str(index): int(value)
        for index, value in counts.items()
    }


def get_trade_context_analytics():
    replay_file = get_replay_journal_path()

    if not replay_file.exists():
        return {
            "status": "failed",
            "reason": "Replay trade file not found."
        }

    df = pd.read_csv(replay_file)

    if df.empty:
        return {
            "status": "failed",
            "reason": "No replay trades found."
        }

    df["return_percent"] = pd.to_numeric(
        df["return_percent"],
        errors="coerce"
    )

    df = df.dropna(subset=["return_percent"])

    winners = df[df["return_percent"] > 0]
    losers = df[df["return_percent"] <= 0]

    return {
        "status": "completed",
        "total_rows_loaded": len(df),

        "winner_count": len(winners),
        "loser_count": len(losers),

        "winner_avg_rsi": average(winners["rsi_at_entry"]),
        "loser_avg_rsi": average(losers["rsi_at_entry"]),

        "winner_avg_distance_ma20": average(winners["distance_ma20"]),
        "loser_avg_distance_ma20": average(losers["distance_ma20"]),

        "winner_avg_distance_ma50": average(winners["distance_ma50"]),
        "loser_avg_distance_ma50": average(losers["distance_ma50"]),

        "winner_avg_trend_strength": average(winners["trend_strength"]),
        "loser_avg_trend_strength": average(losers["trend_strength"]),

        "winner_previous_candle": average(winners["previous_candle_return"]),
        "loser_previous_candle": average(losers["previous_candle_return"]),

        "winner_ma_alignment": count_values(winners["ma_alignment"]),
        "loser_ma_alignment": count_values(losers["ma_alignment"]),

        "winner_rsi_slope": count_values(winners["rsi_slope"]),
        "loser_rsi_slope": count_values(losers["rsi_slope"]),
    }
