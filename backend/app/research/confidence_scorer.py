"""Pure confidence scoring for the modular Research Director."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _research_return_score(result: Mapping[str, Any] | None) -> int:
    if not result:
        return 0

    total_return = float(result.get("total_return", 0))
    if total_return > 3:
        return 15
    if total_return > 1:
        return 10
    if total_return > 0:
        return 5
    return 0


def _walk_forward_score(result: Mapping[str, Any] | None) -> int:
    if not result:
        return 0

    robustness = result.get("robustness")
    if robustness == "PASS":
        return 25
    if robustness == "UNSTABLE":
        return 12
    if robustness == "FAIL":
        return 6
    return 2


def _memory_score(total_tests_saved: int) -> int:
    if total_tests_saved >= 200:
        return 10
    if total_tests_saved >= 100:
        return 7
    if total_tests_saved >= 50:
        return 5
    if total_tests_saved >= 20:
        return 3
    return 0


def confidence_label(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Weak"
    return "Very Weak"


def score_research_confidence(
    *,
    best_strategy_lab: Mapping[str, Any] | None,
    best_parameter_lab: Mapping[str, Any] | None,
    best_evolution_lab: Mapping[str, Any] | None,
    best_walk_forward: Mapping[str, Any] | None,
    total_tests_saved: int,
    live_score: int,
) -> dict[str, int | str]:
    """Return the legacy Research Director confidence score and label."""
    raw_score = sum(
        _research_return_score(result)
        for result in (
            best_strategy_lab,
            best_parameter_lab,
            best_evolution_lab,
        )
    )
    raw_score += _walk_forward_score(best_walk_forward)
    raw_score += _memory_score(int(total_tests_saved))
    raw_score += int(live_score)

    score = min(raw_score, 100)
    return {
        "confidence_score": score,
        "confidence_label": confidence_label(score),
    }
