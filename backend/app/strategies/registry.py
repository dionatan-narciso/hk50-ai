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

    def __len__(self) -> int:
        return len(self._strategies)

    def __contains__(self, name: object) -> bool:
        return name in self._strategies
