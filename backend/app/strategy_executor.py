from app.market_regime_detector import detect_market_regime
from app.strategies.breakout import BreakoutStrategy
from app.strategies.contracts import MarketContext
from app.strategies.default_registry import build_default_strategy_registry
from app.strategies.ma_alignment import MaAlignmentStrategy
from app.strategies.numbers import clean_number
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


def extract_strategy_name(best_strategy):
    if isinstance(best_strategy, dict):
        return str(best_strategy.get("strategy", "")).lower()

    return str(best_strategy).lower()


def is_strategy_blocked_by_regime(strategy_name, regime_data):
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


def resolve_registered_strategy_name(strategy_name):
    """Map existing research names to the canonical plugin registry names."""
    if "rsi" in strategy_name or "pullback" in strategy_name:
        return "RSI Pullback"

    if "ma" in strategy_name or "moving" in strategy_name or "alignment" in strategy_name:
        return "MA Alignment"

    if "breakout" in strategy_name:
        return "Breakout"

    return "Trend Following"


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

    if "rsi<30" in strategy_name or "rsi < 30" in strategy_name:
        rsi = clean_number(market_data.get("rsi"), 50)
        risk = market_data.get("risk", "Medium")

        if rsi < 30 and risk != "High":
            signal = "BUY"
            reason = "RSI < 30 strategy triggered BUY."
        else:
            signal = "HOLD"
            reason = "RSI < 30 strategy found no valid setup."
    else:
        registry = build_default_strategy_registry()
        plugin_name = resolve_registered_strategy_name(strategy_name)
        strategy = registry.get(plugin_name)
        signal, reason = _execute_plugin(strategy, market_data)

    return {
        "strategy_used": best_strategy,
        "signal": signal,
        "strategy_reason": reason,
        "market_regime": regime_data,
    }
