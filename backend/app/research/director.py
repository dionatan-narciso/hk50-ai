"""Modular Research Director with behavior matching the legacy implementation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.live_performance_memory import load_live_strategy_performance
from app.research.live_performance import rank_live_performance
from app.research_engine import (
    run_evolution_lab,
    run_parameter_lab,
    run_research_memory,
    run_strategy_lab,
    run_walk_forward_lab,
)
from app.trade_analytics import run_trade_analytics


def _analytics_bonus(strategy_name: str, rows: Sequence[Mapping[str, Any]]) -> int:
    for row in rows:
        if row.get("strategy") != strategy_name:
            continue
        average_return = float(row.get("average_return", 0))
        trades = int(row.get("trades", 0))
        if trades >= 5:
            if average_return > 0.5:
                return 10
            if average_return > 0:
                return 5
            if average_return < 0:
                return -5
    return 0


def build_research_director_result(
    *,
    strategy_lab: Sequence[Mapping[str, Any]],
    parameter_lab: Sequence[Mapping[str, Any]],
    evolution_lab: Sequence[Mapping[str, Any]],
    walk_forward: Sequence[Mapping[str, Any]],
    memory: Mapping[str, Any],
    analytics: Mapping[str, Any],
    live_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    strategy_analytics = analytics.get("strategy_performance", [])
    memory_best_strategy = memory.get("best_strategy")
    worst_strategy = memory.get("worst_strategy")

    profitable_strategy_count = len([s for s in strategy_lab if s["total_return"] > 0])
    profitable_parameter_count = len([s for s in parameter_lab if s["total_return"] > 0])
    profitable_evolution_count = len([s for s in evolution_lab if s["total_return"] > 0])

    best_strategy_lab = strategy_lab[0] if strategy_lab else None
    best_parameter_lab = parameter_lab[0] if parameter_lab else None
    best_evolution_lab = evolution_lab[0] if evolution_lab else None
    best_walk_forward = walk_forward[0] if walk_forward else None

    live_context = rank_live_performance(live_records)
    live_performance = live_context["live_performance"]
    best_live_strategy = live_context["best_live_strategy"]
    live_score = live_context["live_score"]

    strategy_candidates: list[dict[str, Any]] = []

    def add_candidate(strategy_name: str | None, source: str, research_score: int, live_bonus: int = 0) -> None:
        if not strategy_name:
            return
        analytics_bonus = _analytics_bonus(strategy_name, strategy_analytics)
        strategy_candidates.append({
            "strategy": strategy_name,
            "source": source,
            "research_score": research_score,
            "live_bonus": live_bonus,
            "analytics_bonus": analytics_bonus,
            "final_score": research_score + live_bonus + analytics_bonus,
        })

    if memory_best_strategy:
        add_candidate(
            memory_best_strategy.get("strategy") if isinstance(memory_best_strategy, dict) else memory_best_strategy,
            "Research Memory",
            35,
        )
    if best_strategy_lab:
        add_candidate(best_strategy_lab.get("strategy"), "Strategy Lab", 30)
    if best_parameter_lab:
        add_candidate(best_parameter_lab.get("parameter"), "Parameter Lab", 28)
    if best_evolution_lab:
        add_candidate(best_evolution_lab.get("strategy"), "Evolution Lab", 32)
    if best_walk_forward:
        robustness = best_walk_forward.get("robustness", "UNKNOWN")
        wf_score = 35 if robustness == "PASS" else 22 if robustness == "UNSTABLE" else 10 if robustness == "FAIL" else 5
        add_candidate(best_walk_forward.get("strategy"), "Walk Forward Lab", wf_score)
    if best_live_strategy:
        add_candidate(best_live_strategy.get("strategy"), "Live Performance Memory", 20, live_score)

    if strategy_candidates:
        strategy_candidates = sorted(strategy_candidates, key=lambda row: row["final_score"], reverse=True)
        selected_strategy = strategy_candidates[0]
        best_strategy = selected_strategy["strategy"]
        if best_live_strategy:
            live_total_trades = int(best_live_strategy.get("total_trades", 0))
            live_win_rate = float(best_live_strategy.get("win_rate", 0))
            live_avg_return = float(best_live_strategy.get("average_return", 0))
            live_strategy_name = best_live_strategy.get("strategy")
            live_analytics_bonus = _analytics_bonus(live_strategy_name, strategy_analytics)
            if live_total_trades >= 10 and live_win_rate >= 60 and live_avg_return > 0 and live_score >= 25:
                selected_strategy = {
                    "strategy": live_strategy_name,
                    "source": "Live Performance Override",
                    "research_score": 20,
                    "live_bonus": live_score,
                    "analytics_bonus": live_analytics_bonus,
                    "final_score": 20 + live_score + live_analytics_bonus,
                }
                best_strategy = live_strategy_name
    else:
        selected_strategy = None
        best_strategy = memory_best_strategy

    score = 0
    for best in (best_strategy_lab, best_parameter_lab, best_evolution_lab):
        if best:
            total_return = best["total_return"]
            score += 15 if total_return > 3 else 10 if total_return > 1 else 5 if total_return > 0 else 0

    if best_walk_forward:
        robustness = best_walk_forward["robustness"]
        score += 25 if robustness == "PASS" else 12 if robustness == "UNSTABLE" else 6 if robustness == "FAIL" else 2

    tests_saved = memory.get("total_tests_saved", 0)
    score += 10 if tests_saved >= 200 else 7 if tests_saved >= 100 else 5 if tests_saved >= 50 else 3 if tests_saved >= 20 else 0
    score += live_score

    confidence_score = min(score, 100)
    confidence_label = "Strong" if confidence_score >= 80 else "Moderate" if confidence_score >= 60 else "Weak" if confidence_score >= 40 else "Very Weak"

    recommendations: list[str] = []
    if selected_strategy:
        recommendations.append(
            f"Research Director selected {selected_strategy['strategy']} from {selected_strategy['source']} with final score {selected_strategy['final_score']}."
        )
    if selected_strategy and selected_strategy["source"] == "Live Performance Override":
        recommendations.append("Live performance has enough evidence to override research memory.")
    if best_parameter_lab:
        recommendations.append(f"Best parameter result is {best_parameter_lab['parameter']} with {best_parameter_lab['total_return']}% return.")
    if best_evolution_lab:
        recommendations.append(f"Best evolved strategy is {best_evolution_lab['strategy']} with {best_evolution_lab['total_return']}% return.")
    if best_walk_forward:
        recommendations.append(f"Most robust walk forward result is {best_walk_forward['strategy']} with status {best_walk_forward['robustness']}.")
    if best_live_strategy:
        recommendations.append(
            f"Live paper memory favours {best_live_strategy['strategy']} with {best_live_strategy['win_rate']}% win rate and {best_live_strategy['average_return']}% average return."
        )
    if worst_strategy:
        recommendations.append(f"Avoid or redesign {worst_strategy['strategy']} because it has the weakest saved result.")
    if confidence_score < 60:
        recommendations.append("Research confidence is not strong enough yet. Focus on robustness and live paper performance before trusting live signals.")

    return {
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "profitable_strategy_count": profitable_strategy_count,
        "profitable_parameter_count": profitable_parameter_count,
        "profitable_evolution_count": profitable_evolution_count,
        "best_strategy": best_strategy,
        "selected_strategy": selected_strategy,
        "strategy_candidates": strategy_candidates,
        "worst_strategy": worst_strategy,
        "best_strategy_lab": best_strategy_lab,
        "best_parameter_lab": best_parameter_lab,
        "best_evolution_lab": best_evolution_lab,
        "most_robust": best_walk_forward,
        "live_score": live_score,
        "best_live_strategy": best_live_strategy,
        "live_performance": live_performance,
        "recommendations": recommendations,
    }


def run_research_director() -> dict[str, Any]:
    """Run the modular Research Director using canonical paper state."""
    live_df = load_live_strategy_performance()
    return build_research_director_result(
        strategy_lab=run_strategy_lab().get("strategies", []),
        parameter_lab=run_parameter_lab().get("parameter_tests", []),
        evolution_lab=run_evolution_lab().get("evolution_tests", []),
        walk_forward=run_walk_forward_lab().get("walk_forward_tests", []),
        memory=run_research_memory(),
        analytics=run_trade_analytics(),
        live_records=live_df.to_dict("records"),
    )
