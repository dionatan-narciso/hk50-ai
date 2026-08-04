"""Compatibility wrapper for strategy voting.

Production callers continue importing ``run_strategy_vote`` from this module,
while the implementation now runs through the strategy plugin registry.
"""

from app.strategies.voting import run_registry_strategy_vote


def run_strategy_vote(market_data):
    """Run the default registered strategies using the legacy response contract."""
    return run_registry_strategy_vote(market_data)
