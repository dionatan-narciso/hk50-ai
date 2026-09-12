from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.oos_validation.engine import run_oos_validation_replay
from app.oos_validation.snapshot import load_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


MIN_OOS_TRADES = 5


def _profit_factor(returns: pd.Series) -> float | None:
    positive = float(returns[returns > 0].sum())
    negative = float(-returns[returns < 0].sum())
    if negative == 0:
        return None
    return round(positive / negative, 3)


def _metrics(frame: pd.DataFrame) -> dict[str, Any]:
    empty = {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "average_return": 0.0,
        "median_return": 0.0,
        "total_return": 0.0,
        "profit_factor": None,
    }
    if frame.empty:
        return empty
    returns = pd.to_numeric(frame["return_percent"], errors="coerce").dropna()
    if returns.empty:
        return empty
    wins = int((returns > 0).sum())
    trades = int(len(returns))
    return {
        "trades": trades,
        "wins": wins,
        "losses": trades - wins,
        "win_rate": round((wins / trades) * 100, 2),
        "average_return": round(float(returns.mean()), 3),
        "median_return": round(float(returns.median()), 3),
        "total_return": round(float(returns.sum()), 3),
        "profit_factor": _profit_factor(returns),
    }


def _matches_context(frame: pd.DataFrame, context: dict[str, Any]) -> pd.DataFrame:
    matched = frame
    for column, expected in context.items():
        if column not in matched.columns:
            return matched.iloc[0:0]
        matched = matched.loc[matched[column].fillna("UNKNOWN").astype(str) == str(expected)]
    return matched


def _classification(
    *,
    direction: str,
    validation_metrics: dict[str, Any],
    directional_lift: float,
) -> str:
    if int(validation_metrics["trades"]) < MIN_OOS_TRADES:
        return "INCONCLUSIVE"

    average = float(validation_metrics["average_return"])
    profit_factor = validation_metrics["profit_factor"]
    if direction == "POSITIVE":
        if average <= 0 or directional_lift <= 0:
            return "FAIL"
        if profit_factor is not None and float(profit_factor) <= 1:
            return "FAIL"
        return "PASS"

    if average >= 0 or directional_lift <= 0:
        return "FAIL"
    if profit_factor is not None and float(profit_factor) >= 1:
        return "FAIL"
    return "PASS"


def evaluate_frozen_candidates(*, run_replay: bool = True) -> dict[str, Any]:
    replay_summary = run_oos_validation_replay() if run_replay else None
    paths = resolve_runtime_paths()
    journal = (
        pd.read_csv(paths.validation_trade_journal)
        if paths.validation_trade_journal.exists()
        else pd.DataFrame()
    )
    snapshot = load_candidate_snapshot()
    baseline = _metrics(journal)
    results = []

    for candidate in snapshot.get("candidates", []):
        context = candidate["context"]
        metrics = _metrics(_matches_context(journal, context))
        discovery_average = float(candidate["discovery_average_return"])
        validation_average = float(metrics["average_return"])
        same_sign = (
            validation_average > 0
            if candidate["direction"] == "POSITIVE"
            else validation_average < 0
        )
        retention = None
        if discovery_average != 0 and same_sign:
            retention = round(abs(validation_average / discovery_average), 3)

        baseline_average = float(baseline["average_return"])
        raw_delta = round(validation_average - baseline_average, 3)
        directional_lift = (
            raw_delta
            if candidate["direction"] == "POSITIVE"
            else round(baseline_average - validation_average, 3)
        )
        results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "classification": candidate["classification"],
                "direction": candidate["direction"],
                "context": context,
                "discovery": {
                    "trades": candidate["discovery_trades"],
                    "win_rate": candidate.get("discovery_win_rate"),
                    "average_return": discovery_average,
                    "profit_factor": candidate.get("discovery_profit_factor"),
                    "fold_consistency_percent": candidate.get("discovery_fold_consistency_percent"),
                },
                "validation": metrics,
                "effect_retention_ratio": retention,
                "baseline_average_return_delta": raw_delta,
                "directional_lift_vs_baseline": directional_lift,
                "oos_status": _classification(
                    direction=candidate["direction"],
                    validation_metrics=metrics,
                    directional_lift=directional_lift,
                ),
            }
        )

    status_counts = {
        label: sum(1 for item in results if item["oos_status"] == label)
        for label in ("PASS", "FAIL", "INCONCLUSIVE")
    }
    report = {
        "status": "completed",
        "mode": "frozen_oos_candidate_evaluation",
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "candidate_count": len(results),
        "minimum_oos_trades": MIN_OOS_TRADES,
        "baseline": baseline,
        "status_counts": status_counts,
        "candidates": results,
        "replay_summary": replay_summary,
        "note": (
            "Frozen Sprint 1B hypotheses were evaluated without retuning. "
            "PASS requires enough OOS trades, the expected return direction, supportive profit factor, "
            "and improvement in the expected direction versus the OOS baseline."
        ),
    }
    paths.validation_result_report.parent.mkdir(parents=True, exist_ok=True)
    paths.validation_result_report.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report
