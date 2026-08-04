from __future__ import annotations

from typing import Any


def extract_strategy_name(best_strategy: Any) -> str:
    """Return the existing lower-case strategy name representation."""
    if isinstance(best_strategy, dict):
        return str(best_strategy.get("strategy", "")).lower()
    return str(best_strategy).lower()


def resolve_registered_strategy_name(strategy_name: str) -> str:
    """Map existing research names to canonical execution-registry names."""
    if "rsi<30" in strategy_name or "rsi < 30" in strategy_name:
        return "RSI < 30"
    if "rsi" in strategy_name or "pullback" in strategy_name:
        return "RSI Pullback"
    if "ma" in strategy_name or "moving" in strategy_name or "alignment" in strategy_name:
        return "MA Alignment"
    if "breakout" in strategy_name:
        return "Breakout"
    return "Trend Following"


def is_strategy_blocked_by_regime(strategy_name: str, regime_data: dict) -> bool:
    """Preserve the existing strategy-to-regime blocking aliases."""
    blocked = regime_data.get("blocked_strategies", [])

    if ("rsi<30" in strategy_name or "rsi < 30" in strategy_name) and "RSI < 30" in blocked:
        return True
    if ("rsi" in strategy_name or "pullback" in strategy_name) and "RSI Pullback" in blocked:
        return True
    if ("ma" in strategy_name or "moving" in strategy_name or "alignment" in strategy_name) and "MA Alignment" in blocked:
        return True
    if "breakout" in strategy_name and "Breakout" in blocked:
        return True
    if "trend" in strategy_name and "Trend Following" in blocked:
        return True
    return False
