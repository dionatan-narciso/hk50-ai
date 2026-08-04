from __future__ import annotations

from collections.abc import Iterable

from app.strategies.contracts import Strategy


class StrategyRegistry:
    """Ordered registry for strategy plugin instances."""

    def __init__(self, strategies: Iterable[Strategy] | None = None) -> None:
        self._strategies: dict[str, Strategy] = {}
        for strategy in strategies or ():
            self.register(strategy)

    def register(self, strategy: Strategy) -> None:
        name = strategy.name.strip()
        if not name:
            raise ValueError("Strategy name cannot be empty.")
        if name in self._strategies:
            raise ValueError(f"Strategy {name!r} is already registered.")
        self._strategies[name] = strategy

    def get(self, name: str) -> Strategy:
        try:
            return self._strategies[name]
        except KeyError as exc:
            raise KeyError(f"Strategy {name!r} is not registered.") from exc

    def all(self) -> tuple[Strategy, ...]:
        return tuple(self._strategies.values())

    def names(self) -> tuple[str, ...]:
        return tuple(self._strategies)

    def voting_eligible(self) -> tuple[Strategy, ...]:
        """Return registered strategies that declare voting eligibility."""
        return tuple(
            strategy
            for strategy in self._strategies.values()
            if strategy.metadata.voting_eligible
        )

    def compatible(
        self,
        symbol: str,
        timeframe: str,
        *,
        voting_only: bool = False,
    ) -> tuple[Strategy, ...]:
        """Return strategies declaring support for a market context.

        Capability queries are informational in Sprint 1A.9; existing consumers
        do not automatically filter their explicit registries yet.
        """
        strategies = self.voting_eligible() if voting_only else self.all()
        return tuple(
            strategy
            for strategy in strategies
            if strategy.metadata.supports(symbol, timeframe)
        )

    def __len__(self) -> int:
        return len(self._strategies)

    def __contains__(self, name: object) -> bool:
        return name in self._strategies
