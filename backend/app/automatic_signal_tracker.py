from datetime import datetime
import os
import pandas as pd

from app.live_performance_memory import update_live_strategy_memory
from app.voting_performance_memory import save_voting_result
from app.quality_performance_memory import update_quality_performance_memory
from app.regime_performance_memory import update_regime_memory
from app.confidence_calibration_memory import update_confidence_calibration
from app.daily_risk_manager import check_daily_risk_limits
from app.runtime_paths import resolve_runtime_paths
from app.utils.trade_context import calculate_trade_context


def _paper_state_paths():
    paths = resolve_runtime_paths()
    return paths.paper_open_position, paths.paper_last_signal


def get_adaptive_trailing_settings(atr_percent):
    if atr_percent < 1:
        return {"activation": 0.4, "pullback": 0.2}
    elif atr_percent < 2:
        return {"activation": 0.75, "pullback": 0.35}
    else:
        return {"activation": 1.5, "pullback": 0.75}


def load_open_position():
    open_position_file, _ = _paper_state_paths()

    if not os.path.exists(open_position_file):
        return None

    df = pd.read_csv(open_position_file)
    if df.empty:
        return None

    return df.iloc[0].to_dict()


def save_open_position(position):
    open_position_file, _ = _paper_state_paths()
    open_position_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([position]).to_csv(open_position_file, index=False)


def clear_open_position():
    open_position_file, _ = _paper_state_paths()

    if os.path.exists(open_position_file):
        os.remove(open_position_file)


def load_last_signal():
    _, last_signal_file = _paper_state_paths()

    if not os.path.exists(last_signal_file):
        return None

    df = pd.read_csv(last_signal_file)
    if df.empty:
        return None

    return df.iloc[0]["signal"]


def save_last_signal(signal):
    _, last_signal_file = _paper_state_paths()
    last_signal_file.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([{
        "signal": signal,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }]).to_csv(last_signal_file, index=False)


def run_automatic_signal_tracker(
    symbol,
    current_price,
    signal,
    confidence,
    reason,
    save_trade_function,
    update_memory_function=None,
    vote_signal="UNKNOWN",
    vote_strength=0,
    total_votes=0,
    raw_signal="UNKNOWN",
    atr_percent=1.5,
    quality="UNKNOWN",
    market_data=None,
):
    if market_data is None:
        market_data = {}

    open_position = load_open_position()
    last_signal = load_last_signal()

    trailing_settings = get_adaptive_trailing_settings(float(atr_percent or 1.5))
    activation_threshold = trailing_settings["activation"]
    pullback_threshold = trailing_settings["pullback"]

    trade_event = {
        "status": "no_action",
        "message": "Signal unchanged or no trade action needed"
    }

    signal_changed = signal != last_signal

    if signal_changed:
        save_last_signal(signal)

    allow_trade = True
    risk_block_reason = None

    daily_risk = check_daily_risk_limits()

    if not daily_risk.get("allow_trade", True):
        allow_trade = False
        risk_block_reason = daily_risk.get("reason", "BLOCKED_DAILY_RISK_LIMIT")

    if confidence < 55:
        allow_trade = False
        risk_block_reason = "BLOCKED_LOW_CONFIDENCE"

    if vote_signal in ["BUY", "SELL"] and vote_strength < 3:
        allow_trade = False
        risk_block_reason = "BLOCKED_WEAK_VOTE"

    if raw_signal == "HOLD":
        allow_trade = False
        risk_block_reason = "BLOCKED_RAW_SIGNAL_HOLD"

    if open_position is None and signal == "HOLD":
        trade_event = {
            "status": "no_trade",
            "reason": "SIGNAL_IS_HOLD",
            "confidence": confidence,
            "quality": quality,
            "raw_signal": raw_signal,
            "vote_signal": vote_signal,
            "vote_strength": vote_strength
        }

    elif (
        open_position is None
        and signal in ["BUY", "SELL"]
        and signal_changed
        and allow_trade
    ):
        trade_context = calculate_trade_context(market_data)

        open_position = {
            "symbol": symbol,
            "entry_price": current_price,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "vote_signal": vote_signal,
            "vote_strength": vote_strength,
            "total_votes": total_votes,
            "raw_signal": raw_signal,
            "quality": quality,
            "peak_profit_percent": 0,
            "trailing_active": False,
            "trailing_activation": activation_threshold,
            "trailing_pullback": pullback_threshold,
            "atr_percent_at_entry": atr_percent,
            "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_regime": market_data.get("market_regime", "UNKNOWN"),
            "volatility_regime": market_data.get("volatility_regime", "UNKNOWN"),
            **trade_context,
        }

        save_open_position(open_position)

        trade_event = {
            "status": "opened",
            "position": open_position
        }

    elif (
        open_position is None
        and signal in ["BUY", "SELL"]
        and signal_changed
        and not allow_trade
    ):
        trade_event = {
            "status": "blocked",
            "reason": risk_block_reason,
            "signal": signal,
            "confidence": confidence,
            "vote_signal": vote_signal,
            "vote_strength": vote_strength,
            "raw_signal": raw_signal,
            "daily_risk": daily_risk,
        }

    elif open_position is not None:
        entry_price = float(open_position["entry_price"])
        trade_signal = open_position["signal"]

        move_percent = ((current_price - entry_price) / entry_price) * 100

        if trade_signal == "SELL":
            move_percent = move_percent * -1

        peak_profit_percent = float(open_position.get("peak_profit_percent", 0))
        trailing_active = str(open_position.get("trailing_active", False)) == "True"
        activation_threshold = float(
            open_position.get("trailing_activation", activation_threshold)
        )
        pullback_threshold = float(
            open_position.get("trailing_pullback", pullback_threshold)
        )
        atr_percent_at_entry = float(
            open_position.get("atr_percent_at_entry", atr_percent or 1.5)
        )

        if atr_percent_at_entry < 1:
            adaptive_stop_loss = -0.25
        elif atr_percent_at_entry <= 2:
            adaptive_stop_loss = -0.50
        else:
            adaptive_stop_loss = -1.00

        if move_percent > peak_profit_percent:
            peak_profit_percent = round(move_percent, 3)
            open_position["peak_profit_percent"] = peak_profit_percent

        if move_percent >= activation_threshold:
            trailing_active = True
            open_position["trailing_active"] = True

        should_close = False
        result = "OPEN"

        if move_percent <= adaptive_stop_loss:
            should_close = True
            result = "ADAPTIVE_STOP_LOSS_EXIT"

        elif (
            trailing_active
            and move_percent <= peak_profit_percent - pullback_threshold
        ):
            should_close = True
            result = "TRAILING_PROFIT_EXIT"

        elif (
            signal in ["BUY", "SELL"]
            and signal != trade_signal
            and signal_changed
        ):
            should_close = True
            result = "CLOSED_BY_OPPOSITE_SIGNAL"

        if should_close:
            closed_trade = {
                "symbol": open_position["symbol"],
                "signal": trade_signal,
                "entry_price": entry_price,
                "exit_price": current_price,
                "return_percent": round(move_percent, 3),
                "result": result,
                "confidence": open_position["confidence"],
                "reason": open_position["reason"],
                "vote_signal": open_position.get("vote_signal", "UNKNOWN"),
                "vote_strength": int(open_position.get("vote_strength", 0)),
                "total_votes": int(open_position.get("total_votes", 0)),
                "raw_signal": open_position.get("raw_signal", "UNKNOWN"),
                "peak_profit_percent": peak_profit_percent,
                "trailing_active": trailing_active,
                "trailing_activation": activation_threshold,
                "trailing_pullback": pullback_threshold,
                "adaptive_stop_loss": adaptive_stop_loss,
                "atr_percent_at_entry": atr_percent_at_entry,
                "opened_at": open_position["opened_at"],
                "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "quality": open_position.get("quality", "UNKNOWN"),
                "market_regime": open_position.get("market_regime", "UNKNOWN"),
                "volatility_regime": open_position.get("volatility_regime", "UNKNOWN"),
                "close_at_entry": open_position.get("close_at_entry"),
                "ma20_at_entry": open_position.get("ma20_at_entry"),
                "ma50_at_entry": open_position.get("ma50_at_entry"),
                "distance_ma20": open_position.get("distance_ma20"),
                "distance_ma50": open_position.get("distance_ma50"),
                "previous_candle_return": open_position.get("previous_candle_return"),
                "trend_strength": open_position.get("trend_strength"),
                "ma_alignment": open_position.get("ma_alignment"),
                "rsi_slope": open_position.get("rsi_slope"),
            }

            save_trade_function(closed_trade)

            update_live_strategy_memory(
                strategy_name=closed_trade.get("reason", "Unknown Strategy"),
                trade_return=closed_trade["return_percent"]
            )

            update_quality_performance_memory(
                quality=closed_trade.get("quality", "UNKNOWN"),
                trade_return=closed_trade["return_percent"]
            )

            update_confidence_calibration(
                confidence=closed_trade.get("confidence", 0),
                trade_return=closed_trade["return_percent"]
            )

            update_regime_memory(
                strategy=closed_trade.get("reason", "Unknown"),
                market_regime=closed_trade.get("market_regime", "UNKNOWN"),
                volatility_regime=closed_trade.get("volatility_regime", "UNKNOWN"),
                trade_return=closed_trade["return_percent"],
            )

            save_voting_result(
                vote_signal=closed_trade.get("vote_signal", "UNKNOWN"),
                vote_strength=closed_trade.get("vote_strength", 0),
                total_votes=closed_trade.get("total_votes", 0),
                strategy_signal=closed_trade.get("raw_signal", "UNKNOWN"),
                final_signal=closed_trade.get("signal", "UNKNOWN"),
                trade_result=closed_trade["return_percent"]
            )

            if update_memory_function:
                update_memory_function(closed_trade)

            clear_open_position()
            open_position = None

            trade_event = {
                "status": "closed",
                "trade": closed_trade
            }

        else:
            open_position["peak_profit_percent"] = peak_profit_percent
            open_position["trailing_active"] = trailing_active
            save_open_position(open_position)

            trade_event = {
                "status": "tracking",
                "position": open_position,
                "unrealised_return_percent": round(move_percent, 3),
                "peak_profit_percent": peak_profit_percent,
                "trailing_active": trailing_active,
                "trailing_activation": activation_threshold,
                "trailing_pullback": pullback_threshold,
                "adaptive_stop_loss": adaptive_stop_loss,
                "atr_percent_at_entry": atr_percent_at_entry
            }

    return {
        "last_signal": last_signal,
        "current_signal": signal,
        "signal_changed": signal_changed,
        "open_position": open_position,
        "trade_event": trade_event,
        "daily_risk": daily_risk,
    }
