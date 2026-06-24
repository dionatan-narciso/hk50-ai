import pandas as pd
import os

TRADE_FILE = "data/trade_journal.csv"


def run_trade_analytics():

    if not os.path.exists(TRADE_FILE):
        return {
            "total_trades": 0
        }

    df = pd.read_csv(TRADE_FILE)

    if df.empty:
        return {
            "total_trades": 0
        }

    analytics = {}

    analytics["total_trades"] = len(df)

    if "confidence" in df.columns:
        confidence_stats = (
            df.groupby("confidence")["result_pct"]
            .mean()
            .reset_index()
            .sort_values("result_pct", ascending=False)
        )

        analytics["confidence_performance"] = (
            confidence_stats.to_dict("records")
        )

    if "vote_strength" in df.columns:
        vote_stats = (
            df.groupby("vote_strength")["result_pct"]
            .mean()
            .reset_index()
            .sort_values("result_pct", ascending=False)
        )

        analytics["vote_performance"] = (
            vote_stats.to_dict("records")
        )

    strategy_stats = (
        df.groupby("strategy")["result_pct"]
        .agg(["count", "mean"])
        .reset_index()
    )

    strategy_stats.columns = [
        "strategy",
        "trades",
        "average_return"
    ]

    analytics["strategy_performance"] = (
        strategy_stats.sort_values(
            "average_return",
            ascending=False
        ).to_dict("records")
    )

    if "result" in df.columns:
        exit_stats = (
            df.groupby("result")["result_pct"]
            .mean()
            .reset_index()
            .sort_values("result_pct", ascending=False)
        )

        analytics["exit_performance"] = (
            exit_stats.to_dict("records")
        )

    return analytics