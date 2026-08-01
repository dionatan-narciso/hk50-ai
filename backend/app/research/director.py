"""Modular Research Director with behavior matching the legacy implementation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.live_performance_memory import load_live_strategy_performance
from app.research.candidate_ranker import rank_strategy_candidates
from app.research.confidence_scorer import score_research_confidence
from app.research.live_performance import rank_live_performance
from app.research_engine import (
    run_evolution_lab,
    run_parameter_lab,
    run_research_memory,
    run_strategy_lab,
    run_walk_forward_lab,
)
from app.trade_analytics import run_trade_analytics


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

    candidate_result = rank_strategy_candidates(
        memory_best_strategy=memory_best_strategy,
        best_strategy_lab=best_strategy_lab,
        best_parameter_lab=best_parameter_lab,
        best_evolution_lab=best_evolution_lab,
        best_walk_forward=best_walk_forward,
        best_live_strategy=best_live_strategy,
        live_score=live_score,
        strategy_analytics=strategy_analytics,
    )
    strategy_candidates = candidate_result["strategy_candidates"]
    selected_strategy = candidate_result["selected_strategy"]
    best_strategy = candidate_result["best_strategy"]

    confidence = score_research_confidence(
        best_strategy_lab=best_strategy_lab,
        best_parameter_lab=best_parameter_lab,
        best_evolution_lab=best_evolution_lab,
        best_walk_forward=best_walk_forward,
        total_tests_saved=memory.get("total_tests_saved", 0),
        live_score=live_score,
    )
    confidence_score = confidence["confidence_score"]
    confidence_label = confidence["confidence_label"]

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
