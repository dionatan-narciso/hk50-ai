"""Strategy plugin contracts and registry.

Sprint 1A introduces these abstractions without wiring them into the existing
strategy executor or voting engine. Existing trading behaviour remains unchanged.
"""

from app.strategies.contracts import MarketContext, Strategy, StrategyDecision
from app.strategies.registry import StrategyRegistry

__all__ = [
    "MarketContext",
    "Strategy",
    "StrategyDecision",
    "StrategyRegistry",
]
