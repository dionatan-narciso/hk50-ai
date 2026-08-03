"""Load all runtime inputs required by the modular Research Director."""

from __future__ import annotations

from typing import Any

from app.live_performance_memory import load_live_strategy_performance
from app.research_engine import (
    run_evolution_lab,
    run_parameter_lab,
    run_research_memory,
    run_strategy_lab,
    run_walk_forward_lab,
)
from app.trade_analytics import run_trade_analytics


def load_research_sources() -> dict[str, Any]:
    """Return the legacy Research Director inputs using canonical paper state."""
    live_df = load_live_strategy_performance()

    return {
        "strategy_lab": run_strategy_lab().get("strategies", []),
        "parameter_lab": run_parameter_lab().get("parameter_tests", []),
        "evolution_lab": run_evolution_lab().get("evolution_tests", []),
        "walk_forward": run_walk_forward_lab().get("walk_forward_tests", []),
        "memory": run_research_memory(),
        "analytics": run_trade_analytics(),
        "live_records": live_df.to_dict("records"),
    }
