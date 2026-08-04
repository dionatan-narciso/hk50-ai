from app.market_regime_detector import detect_market_regime
from app.strategies.breakout import BreakoutStrategy
from app.strategies.contracts import MarketContext
from app.strategies.default_registry import build_execution_strategy_registry
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.resolution import (
    extract_strategy_name,
    is_strategy_blocked_by_regime,
    resolve_registered_strategy_name,
)
from app.strategies.rsi_pullback import RsiPullbackStrategy
from app.strategies.trend_following import TrendFollowingStrategy


def _execute_plugin(strategy, market_data):
    decision = strategy.evaluate(
        MarketContext(
            symbol="HK50",
            timeframe="1h",
            data=market_data,
        )
    )
    return decision.signal, decision.reason


def execute_trend_following(market_data):
    """Compatibility wrapper for existing callers."""
    return _execute_plugin(TrendFollowingStrategy(), market_data)


def execute_rsi_pullback(market_data):
    """Compatibility wrapper for existing callers."""
    return _execute_plugin(RsiPullbackStrategy(), market_data)


def execute_ma_alignment(market_data):
    """Compatibility wrapper for existing callers."""
    return _execute_plugin(MaAlignmentStrategy(), market_data)


def execute_breakout(market_data):
    """Compatibility wrapper for existing callers."""
    return _execute_plugin(BreakoutStrategy(), market_data)


def execute_strategy(best_strategy, market_data):
    strategy_name = extract_strategy_name(best_strategy)
    regime_data = detect_market_regime(market_data)

    if is_strategy_blocked_by_regime(strategy_name, regime_data):
        return {
            "strategy_used": best_strategy,
            "signal": "HOLD",
            "strategy_reason": (
                f"Strategy blocked by market regime. "
                f"{regime_data.get('reason')}"
            ),
            "market_regime": regime_data,
        }

    registry = build_execution_strategy_registry()
    plugin_name = resolve_registered_strategy_name(strategy_name)
    strategy = registry.get(plugin_name)
    signal, reason = _execute_plugin(strategy, market_data)

    return {
        "strategy_used": best_strategy,
        "signal": signal,
        "strategy_reason": reason,
        "market_regime": regime_data,
    }
