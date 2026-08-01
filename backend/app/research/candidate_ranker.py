"""Pure strategy-candidate ranking for the modular Research Director."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def get_analytics_bonus(
    strategy_name: str | None,
    rows: Sequence[Mapping[str, Any]],
) -> int:
    """Return the legacy paper-trade analytics adjustment for one strategy."""
    if not strategy_name:
        return 0

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


def get_walk_forward_candidate_score(robustness: str) -> int:
    """Return the legacy candidate score for a walk-forward result."""
    if robustness == "PASS":
        return 35
    if robustness == "UNSTABLE":
        return 22
    if robustness == "FAIL":
        return 10
    return 5


def _strategy_name(memory_best_strategy: Any) -> str | None:
    if isinstance(memory_best_strategy, Mapping):
        return memory_best_strategy.get("strategy")
    return memory_best_strategy


def rank_strategy_candidates(
    *,
    memory_best_strategy: Any,
    best_strategy_lab: Mapping[str, Any] | None,
    best_parameter_lab: Mapping[str, Any] | None,
    best_evolution_lab: Mapping[str, Any] | None,
    best_walk_forward: Mapping[str, Any] | None,
    best_live_strategy: Mapping[str, Any] | None,
    live_score: int,
    strategy_analytics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build, sort, and select candidates using the legacy director rules."""
    candidates: list[dict[str, Any]] = []

    def add_candidate(
        strategy_name: str | None,
        source: str,
        research_score: int,
        live_bonus: int = 0,
    ) -> None:
        if not strategy_name:
            return

        analytics_bonus = get_analytics_bonus(strategy_name, strategy_analytics)
        candidates.append(
            {
                "strategy": strategy_name,
                "source": source,
                "research_score": research_score,
                "live_bonus": live_bonus,
                "analytics_bonus": analytics_bonus,
                "final_score": research_score + live_bonus + analytics_bonus,
            }
        )

    add_candidate(_strategy_name(memory_best_strategy), "Research Memory", 35)

    if best_strategy_lab:
        add_candidate(best_strategy_lab.get("strategy"), "Strategy Lab", 30)

    if best_parameter_lab:
        add_candidate(best_parameter_lab.get("parameter"), "Parameter Lab", 28)

    if best_evolution_lab:
        add_candidate(best_evolution_lab.get("strategy"), "Evolution Lab", 32)

    if best_walk_forward:
        add_candidate(
            best_walk_forward.get("strategy"),
            "Walk Forward Lab",
            get_walk_forward_candidate_score(
                str(best_walk_forward.get("robustness", "UNKNOWN"))
            ),
        )

    if best_live_strategy:
        add_candidate(
            best_live_strategy.get("strategy"),
            "Live Performance Memory",
            20,
            live_score,
        )

    if not candidates:
        return {
            "strategy_candidates": [],
            "selected_strategy": None,
            "best_strategy": memory_best_strategy,
        }

    candidates = sorted(
        candidates,
        key=lambda row: row["final_score"],
        reverse=True,
    )
    selected_strategy = candidates[0]
    best_strategy = selected_strategy["strategy"]

    if best_live_strategy:
        live_total_trades = int(best_live_strategy.get("total_trades", 0))
        live_win_rate = float(best_live_strategy.get("win_rate", 0))
        live_average_return = float(best_live_strategy.get("average_return", 0))
        live_strategy_name = best_live_strategy.get("strategy")

        if (
            live_total_trades >= 10
            and live_win_rate >= 60
            and live_average_return > 0
            and live_score >= 25
        ):
            analytics_bonus = get_analytics_bonus(
                live_strategy_name,
                strategy_analytics,
            )
            selected_strategy = {
                "strategy": live_strategy_name,
                "source": "Live Performance Override",
                "research_score": 20,
                "live_bonus": live_score,
                "analytics_bonus": analytics_bonus,
                "final_score": 20 + live_score + analytics_bonus,
            }
            best_strategy = live_strategy_name

    return {
        "strategy_candidates": candidates,
        "selected_strategy": selected_strategy,
        "best_strategy": best_strategy,
    }
