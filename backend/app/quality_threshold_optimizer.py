from app.historical_replay_engine import run_historical_replay


def optimize_quality_threshold():

    thresholds = [50, 55, 60, 65, 70, 75, 80]

    results = []

    for threshold in thresholds:

        result = run_historical_replay(
            period="1y",
            interval="1h",
            quality_threshold=threshold
        )

        results.append({
            "threshold": threshold,
            "trades": result["total_trades"],
            "wins": result["wins"],
            "losses": result["losses"],
            "win_rate": result["win_rate"],
            "average_return": result["average_return"]
        })

    best = max(
        results,
        key=lambda x: (
            x["average_return"],
            x["win_rate"]
        )
    )

    return {
        "status": "completed",
        "best_threshold": best,
        "results": results
    }