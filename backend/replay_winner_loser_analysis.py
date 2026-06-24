import os
import pandas as pd

REPLAY_FILE = "data/replay/replay_trade_journal.csv"


def safe_average(df, column):
    if column not in df.columns or len(df) == 0:
        return None

    return round(df[column].mean(), 3)


def analyze_winners_vs_losers():

    if not os.path.exists(REPLAY_FILE):
        return {"status": "no_replay_data"}

    df = pd.read_csv(REPLAY_FILE)

    if len(df) == 0:
        return {"status": "empty_replay"}

    winners = df[df["return_percent"] > 0]
    losers = df[df["return_percent"] <= 0]

    return {
        "status": "completed",

        "winner_count": len(winners),
        "loser_count": len(losers),

        "winner_avg_confidence": safe_average(winners, "confidence"),

        "loser_avg_confidence": safe_average(losers, "confidence"),

        "winner_avg_rsi": safe_average(winners, "rsi_at_entry"),
        "loser_avg_rsi": safe_average(losers, "rsi_at_entry"),

        "winner_avg_atr": safe_average(winners, "atr_percent_at_entry"),
        "loser_avg_atr": safe_average(losers, "atr_percent_at_entry"),

        "winner_avg_quality": safe_average(winners, "quality_score"),

        "loser_avg_quality": safe_average(losers, "quality_score"),

        "winner_trend_counts": winners["trend_at_entry"].value_counts().to_dict() if "trend_at_entry" in winners.columns else {},
        "loser_trend_counts": losers["trend_at_entry"].value_counts().to_dict() if "trend_at_entry" in losers.columns else {},

        "winner_risk_counts": winners["risk_at_entry"].value_counts().to_dict() if "risk_at_entry" in winners.columns else {},
        "loser_risk_counts": losers["risk_at_entry"].value_counts().to_dict() if "risk_at_entry" in losers.columns else {},
    }