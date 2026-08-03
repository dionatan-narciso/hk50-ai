"""Modular Research Director with behavior matching the legacy implementation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.research.candidate_ranker import rank_strategy_candidates
from app.research.confidence_scorer import score_research_confidence
from app.research.live_performance import rank_live_performance
from app.research.recommendation_builder import build_research_recommendations
from app.research.source_loader import load_research_sources


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

    recommendations = build_research_recommendations(
        selected_strategy=selected_strategy,
        best_parameter_lab=best_parameter_lab,
        best_evolution_lab=best_evolution_lab,
        best_walk_forward=best_walk_forward,
        best_live_strategy=best_live_strategy,
        worst_strategy=worst_strategy,
        confidence_score=confidence_score,
    )

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
    """Load runtime sources and build the modular Research Director result."""
    return build_research_director_result(**load_research_sources())
