from __future__ import annotations

from app.strategies.registry import StrategyRegistry


def validate_strategy_registry(
    registry: StrategyRegistry,
    *,
    symbol: str,
    timeframe: str,
    require_voting_eligible: bool = False,
) -> StrategyRegistry:
    """Validate that every registered plugin supports its intended use.

    The registry is returned unchanged so builders can validate inline. Validation
    is deliberately construction-time only; strategy evaluation and vote rules
    remain unchanged.
    """
    incompatible = [
        strategy.name
        for strategy in registry.all()
        if not strategy.metadata.supports(symbol, timeframe)
    ]
    if incompatible:
        names = ", ".join(incompatible)
        raise ValueError(
            f"Strategy registry contains plugins incompatible with "
            f"{symbol}/{timeframe}: {names}."
        )

    if require_voting_eligible:
        non_voting = [
            strategy.name
            for strategy in registry.all()
            if not strategy.metadata.voting_eligible
        ]
        if non_voting:
            names = ", ".join(non_voting)
            raise ValueError(
                f"Voting registry contains non-voting strategies: {names}."
            )

    return registry
