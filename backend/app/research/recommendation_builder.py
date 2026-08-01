"""Pure recommendation builder for the modular Research Director."""

from __future__ import annotations

from typing import Any, Mapping


def build_research_recommendations(
    *,
    selected_strategy: Mapping[str, Any] | None,
    best_parameter_lab: Mapping[str, Any] | None,
    best_evolution_lab: Mapping[str, Any] | None,
    best_walk_forward: Mapping[str, Any] | None,
    best_live_strategy: Mapping[str, Any] | None,
    worst_strategy: Mapping[str, Any] | None,
    confidence_score: int,
) -> list[str]:
    """Return recommendation messages in the legacy order and wording."""
    recommendations: list[str] = []

    if selected_strategy:
        recommendations.append(
            f"Research Director selected {selected_strategy['strategy']} from "
            f"{selected_strategy['source']} with final score "
            f"{selected_strategy['final_score']}."
        )

    if (
        selected_strategy
        and selected_strategy["source"] == "Live Performance Override"
    ):
        recommendations.append(
            "Live performance has enough evidence to override research memory."
        )

    if best_parameter_lab:
        recommendations.append(
            f"Best parameter result is {best_parameter_lab['parameter']} "
            f"with {best_parameter_lab['total_return']}% return."
        )

    if best_evolution_lab:
        recommendations.append(
            f"Best evolved strategy is {best_evolution_lab['strategy']} "
            f"with {best_evolution_lab['total_return']}% return."
        )

    if best_walk_forward:
        recommendations.append(
            f"Most robust walk forward result is "
            f"{best_walk_forward['strategy']} with status "
            f"{best_walk_forward['robustness']}."
        )

    if best_live_strategy:
        recommendations.append(
            f"Live paper memory favours {best_live_strategy['strategy']} "
            f"with {best_live_strategy['win_rate']}% win rate and "
            f"{best_live_strategy['average_return']}% average return."
        )

    if worst_strategy:
        recommendations.append(
            f"Avoid or redesign {worst_strategy['strategy']} because it has "
            "the weakest saved result."
        )

    if confidence_score < 60:
        recommendations.append(
            "Research confidence is not strong enough yet. Focus on robustness "
            "and live paper performance before trusting live signals."
        )

    return recommendations
