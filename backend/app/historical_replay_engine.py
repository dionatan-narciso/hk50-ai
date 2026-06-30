import os
import pandas as pd
import yfinance as yf

from app.market_regime_detector import detect_market_regime
from app.strategy_executor import execute_strategy
from app.strategy_rotation_engine import rotate_strategy
from app.utils.trade_context import calculate_trade_context

from replay_penalty_engine import get_replay_penalty
from replay_learning_controller import record_replay_control_result
from app.entry_context_scoring import calculate_entry_context_score

from app.entry_learning_memory import (update_entry_weights_after_replay)

from app.trade_quality_score import calculate_trade_quality_score

from app.support_resistance_engine import analyse_support_resistance

from app.support_resistance_learning_memory import get_learned_sr_weight

REPLAY_DIR = "data/replay"
REPLAY_TRADES_FILE = f"{REPLAY_DIR}/replay_trade_journal.csv"


def ensure_replay_folder():
    os.makedirs(REPLAY_DIR, exist_ok=True)


def reset_replay_files():
    ensure_replay_folder()
    if os.path.exists(REPLAY_TRADES_FILE):
        os.remove(REPLAY_TRADES_FILE)


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    return true_range.rolling(period).mean()


def load_hk50_history(period="1y", interval="1h"):
    df = yf.download(
        "^HSI",
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False
    )

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = calculate_rsi(df["Close"])
    df["ATR"] = calculate_atr(df)
    df["ATR_PERCENT"] = (df["ATR"] / df["Close"]) * 100

    return df.dropna()


def classify_trend(row):
    if row["Close"] > row["MA20"] > row["MA50"]:
        return "Bullish"
    if row["Close"] < row["MA20"] < row["MA50"]:
        return "Bearish"
    return "Neutral"


def classify_risk(atr_percent):
    if atr_percent >= 1.5:
        return "High"
    if atr_percent >= 1:
        return "Medium"
    return "Low"


def get_replay_research_context():
    return {
        "best_strategy": "RSI < 30",
        "most_robust_strategy": "Trend Following",
        "director_confidence": 56,
        "confidence_label": "Replay",
        "director_available": True,
    }


def save_replay_trade(trade):
    ensure_replay_folder()

    if os.path.exists(REPLAY_TRADES_FILE):
        df = pd.read_csv(REPLAY_TRADES_FILE)
        df = pd.concat([df, pd.DataFrame([trade])], ignore_index=True)
    else:
        df = pd.DataFrame([trade])

    df.to_csv(REPLAY_TRADES_FILE, index=False)


def get_adaptive_replay_settings(atr_percent):
    if atr_percent < 1:
        return {
            "activation": 0.4,
            "pullback": 0.2,
            "stop_loss": -0.25,
        }

    if atr_percent < 2:
        return {
            "activation": 0.75,
            "pullback": 0.35,
            "stop_loss": -0.5,
        }

    return {
        "activation": 1.5,
        "pullback": 0.75,
        "stop_loss": -1.0,
    }


def calculate_replay_confidence(row):
    confidence = 56

    rsi = float(row["RSI"])
    close = float(row["Close"])
    ma20 = float(row["MA20"])
    ma50 = float(row["MA50"])
    atr_percent = float(row["ATR_PERCENT"])

    if rsi < 25:
        confidence += 8
    elif rsi < 30:
        confidence += 5
    elif rsi < 35:
        confidence += 2

    if close > ma20:
        confidence += 3

    if ma20 > ma50:
        confidence += 3

    if atr_percent < 0.5:
        confidence += 3
    elif atr_percent > 1.2:
        confidence -= 5

    return max(0, min(100, round(confidence)))


def build_market_snapshot(row, previous_row=None, recent_candles=None):
    price = float(row["Close"])
    atr_percent = float(row["ATR_PERCENT"])

    previous_close = (
        float(previous_row["Close"])
        if previous_row is not None
        else price
    )

    previous_rsi = (
        float(previous_row["RSI"])
        if previous_row is not None
        else float(row["RSI"])
    )

    support_resistance = {}

    if recent_candles:
        support_resistance = analyse_support_resistance(
            candles=recent_candles,
            current_price=price
        )

    return {
        "price": price,
        "close": price,
        "previous_close": previous_close,
        "rsi": float(row["RSI"]),
        "previous_rsi": previous_rsi,
        "ma20": float(row["MA20"]),
        "ma50": float(row["MA50"]),
        "atr_percent": round(atr_percent, 3),
        "trend": classify_trend(row),
        "risk": classify_risk(atr_percent),
        "confidence": calculate_replay_confidence(row),

        "support_resistance": support_resistance,
        "nearest_support": support_resistance.get("nearest_support"),
        "support_strength": support_resistance.get("support_strength"),
        "nearest_resistance": support_resistance.get("nearest_resistance"),
        "resistance_strength": support_resistance.get("resistance_strength"),
        "distance_to_support": support_resistance.get("distance_to_support"),
        "distance_to_resistance": support_resistance.get("distance_to_resistance"),
        "support_resistance_status": support_resistance.get(
            "support_resistance_status",
            "UNKNOWN"
        ),
    }

def run_ai_replay_decision(market_snapshot):
    research_context = get_replay_research_context()
    best_strategy = research_context.get("best_strategy", "Trend Following")

    initial_strategy_result = execute_strategy(best_strategy, market_snapshot)

    market_regime = initial_strategy_result.get(
        "market_regime",
        detect_market_regime(market_snapshot)
    )

    rotation_result = rotate_strategy(
        current_strategy=best_strategy,
        market_regime=market_regime.get("market_regime", "UNKNOWN"),
        volatility_regime=market_regime.get("volatility_regime", "UNKNOWN"),
        research_context=research_context,
    )

    rotated_strategy = rotation_result.get("selected_strategy", best_strategy)
    strategy_result = execute_strategy(rotated_strategy, market_snapshot)

    market_regime = strategy_result.get("market_regime", market_regime)

    return {
        "strategy": rotated_strategy,
        "original_strategy": best_strategy,
        "signal": strategy_result.get("signal", "HOLD"),
        "reason": strategy_result.get("strategy_reason", ""),
        "market_regime": market_regime.get("market_regime", "UNKNOWN"),
        "volatility_regime": market_regime.get("volatility_regime", "UNKNOWN"),
        "rotation_changed": rotation_result.get("rotation_changed_strategy", False),
        "rotation_reason": rotation_result.get("rotation_reason"),
        "rotation_scores": rotation_result.get("rotation_scores", []),
    }

def calculate_support_resistance_replay_adjustment(market_snapshot):
    distance_to_support = market_snapshot.get("distance_to_support")
    distance_to_resistance = market_snapshot.get("distance_to_resistance")

    adjustment = 0
    reasons = []

    try:
        distance_to_support = (
            float(distance_to_support)
            if distance_to_support is not None
            else None
        )
    except Exception:
        distance_to_support = None

    try:
        distance_to_resistance = (
            float(distance_to_resistance)
            if distance_to_resistance is not None
            else None
        )
    except Exception:
        distance_to_resistance = None

    if distance_to_resistance is not None:
        if distance_to_resistance >= 2.0:
            adjustment += 4
            reasons.append("Distance to resistance 2%+ bonus +4")
        elif distance_to_resistance <= 0.25:
            adjustment -= 5
            reasons.append("Very close to resistance penalty -5")
        elif distance_to_resistance <= 0.50:
            adjustment -= 2
            reasons.append("Close to resistance penalty -2")

    if distance_to_support is not None:
        if 0.25 <= distance_to_support <= 0.50:
            adjustment += 3
            reasons.append("Healthy distance above support bonus +3")
        elif 0.50 < distance_to_support <= 1.00:
            adjustment += 2
            reasons.append("Moderate distance above support bonus +2")
        elif distance_to_support <= 0.25:
            adjustment -= 2
            reasons.append("Too close to support penalty -2")
        elif 1.00 < distance_to_support <= 2.00:
            adjustment -= 4
            reasons.append("Weak support distance penalty -4")

    return {
        "support_resistance_adjustment": adjustment,
        "support_resistance_reasons": reasons,
    }

def calculate_learned_support_resistance_adjustment(market_snapshot, base_adjustment):
    learned_adjustment = 0
    reasons = []

    conditions = [
        (
            "support_resistance_status",
            market_snapshot.get("support_resistance_status")
        ),
        (
            "support_strength",
            market_snapshot.get("support_strength")
        ),
        (
            "resistance_strength",
            market_snapshot.get("resistance_strength")
        ),
        (
            "support_resistance_adjustment",
            base_adjustment
        ),
    ]

    for condition_type, condition_value in conditions:
        if condition_value is None:
            continue

        weight = get_learned_sr_weight(
            condition_type=condition_type,
            condition_value=condition_value
        )

        if weight != 0:
            learned_adjustment += weight
            reasons.append(
                f"{condition_type}={condition_value} learned weight {weight}"
            )

    learned_adjustment = max(-8, min(8, learned_adjustment))

    return {
        "learned_support_resistance_adjustment": learned_adjustment,
        "learned_support_resistance_reasons": reasons,
    }

def run_historical_replay(
    period="1y",
    interval="1h",
    entry_weights_override=None,
    quality_threshold=None,
):
    ensure_replay_folder()
    reset_replay_files()

    df = load_hk50_history(period=period, interval=interval)

    if df.empty:
        return {
            "status": "failed",
            "reason": "No historical data returned."
        }

    open_position = None
    trades = []
    blocked_by_learning = 0

    previous_row = None

    for index_position, (timestamp, row) in enumerate(df.iterrows()):
        recent_df = df.iloc[max(0, index_position - 80):index_position + 1]

        recent_candles = []

        for _, candle in recent_df.iterrows():
            recent_candles.append({
                "high": float(candle["High"]),
                "low": float(candle["Low"]),
                "close": float(candle["Close"]),
            })
        market_snapshot = build_market_snapshot(
            row=row,
            previous_row=previous_row,
            recent_candles=recent_candles
        )

        price = market_snapshot["price"]
        atr_percent = market_snapshot["atr_percent"]

        decision = run_ai_replay_decision(market_snapshot)

        signal = decision.get("signal", "HOLD")
        strategy = decision.get("strategy", "UNKNOWN")
        confidence = market_snapshot.get("confidence", 56)

        market_regime = decision.get("market_regime", "UNKNOWN")
        volatility_regime = decision.get("volatility_regime", "UNKNOWN")
        rotation_changed = decision.get("rotation_changed", False)

        settings = get_adaptive_replay_settings(atr_percent)

        if open_position is None and signal in ["BUY", "SELL"]:

            penalty = get_replay_penalty(
                strategy=strategy,
                market_regime=market_regime,
                volatility_regime=volatility_regime,
                rotation_changed=rotation_changed
            )

            replay_learning_adjustment = penalty.get("total_adjustment", 0)

            trade_context = calculate_trade_context(market_snapshot)
            market_snapshot.update(trade_context)

            entry_context_score = calculate_entry_context_score(
                market_snapshot,
                entry_weights_override=entry_weights_override
            )

            support_resistance_score = calculate_support_resistance_replay_adjustment(
            market_snapshot
        )

            learned_support_resistance_score = (
            calculate_learned_support_resistance_adjustment(
                market_snapshot=market_snapshot,
                base_adjustment=support_resistance_score.get(
                    "support_resistance_adjustment",
                    0
                )
            )
        )

            trade_quality = calculate_trade_quality_score(
                market_snapshot,
                entry_context_score=entry_context_score
            )

            adjusted_confidence = max(
                0,
                min(
                    100,
                confidence
                + replay_learning_adjustment
                + entry_context_score.get("entry_context_adjustment", 0)
                + support_resistance_score.get("support_resistance_adjustment", 0)
                + learned_support_resistance_score.get(
                    "learned_support_resistance_adjustment",
                    0
                )
               )
             )

            print("REPLAY DEBUG:", {
                "strategy": strategy,
                "confidence": confidence,
                "adjustment": replay_learning_adjustment,
                "entry_context_adjustment": entry_context_score.get(
                    "entry_context_adjustment",
                    0
                ),
                "support_resistance_adjustment": support_resistance_score.get(
                    "support_resistance_adjustment",
                    0
                ),
                "learned_support_resistance_adjustment": learned_support_resistance_score.get(
                    "learned_support_resistance_adjustment",
                    0
                ),
                "adjusted_confidence": adjusted_confidence,
                "threshold": 55
            })

            if adjusted_confidence <= 55:
                blocked_by_learning += 1
                previous_row = row
                continue

            if support_resistance_score.get("support_resistance_adjustment", 0) <= -3:
                blocked_by_learning += 1
                previous_row = row
                continue

            if (
                quality_threshold is not None
                and trade_quality["trade_quality_score"] < quality_threshold
            ):
                blocked_by_learning += 1
                previous_row = row
                continue

            open_position = {
                "strategy": strategy,
                "original_strategy": decision.get("original_strategy"),
                "signal": signal,
                "entry_price": price,
                "opened_at": str(timestamp),
                "peak_profit_percent": 0,
                "atr_percent_at_entry": atr_percent,
                "market_regime": market_regime,
                "volatility_regime": volatility_regime,
                "confidence": adjusted_confidence,
                "original_confidence": confidence,
                "replay_learning_adjustment": replay_learning_adjustment,
                "replay_learning_reasons": " | ".join(penalty.get("reasons", [])),
                "entry_context_adjustment": entry_context_score.get("entry_context_adjustment", 0),
                "support_resistance_adjustment": support_resistance_score.get(
                "support_resistance_adjustment",
                0
                ),
                "support_resistance_reasons": " | ".join(
                    support_resistance_score.get("support_resistance_reasons", [])
                ),
                "learned_support_resistance_adjustment": learned_support_resistance_score.get(
                "learned_support_resistance_adjustment",
                0
            ),
                "learned_support_resistance_reasons": " | ".join(
                learned_support_resistance_score.get(
                    "learned_support_resistance_reasons",
                    []
                )
            ),
                "trade_quality_score": trade_quality.get("trade_quality_score"),
                "trade_quality_label": trade_quality.get("trade_quality_label"),
                "trade_quality_reasons": " | ".join(trade_quality.get("trade_quality_reasons", [])),
                "entry_context_reasons": " | ".join(entry_context_score.get("entry_context_reasons", [])),
                "trade_quality_score": trade_quality.get("trade_quality_score"),
                "trade_quality_label": trade_quality.get("trade_quality_label"),
                "trade_quality_reasons": " | ".join(trade_quality.get("trade_quality_reasons", [])),
                "rotation_changed": rotation_changed,
                "rotation_reason": decision.get("rotation_reason"),
                "strategy_reason": decision.get("reason"),
                "trailing_activation": settings["activation"],
                "trailing_pullback": settings["pullback"],
                "adaptive_stop_loss": settings["stop_loss"],
                "rsi_at_entry": market_snapshot.get("rsi"),
                "trend_at_entry": market_snapshot.get("trend"),
                "risk_at_entry": market_snapshot.get("risk"),
                "support_resistance_status": market_snapshot.get("support_resistance_status"),
                "nearest_support": market_snapshot.get("nearest_support"),
                "nearest_resistance": market_snapshot.get("nearest_resistance"),
                "distance_to_support": market_snapshot.get("distance_to_support"),
                "distance_to_resistance": market_snapshot.get("distance_to_resistance"),
                "support_strength": market_snapshot.get("support_strength"),
                "resistance_strength": market_snapshot.get("resistance_strength"),
                **trade_context,
            }

        elif open_position is not None:
            entry_price = float(open_position["entry_price"])
            trade_signal = open_position["signal"]

            move_percent = ((price - entry_price) / entry_price) * 100

            if trade_signal == "SELL":
                move_percent *= -1

            peak_profit = max(
                float(open_position.get("peak_profit_percent", 0)),
                move_percent
            )

            open_position["peak_profit_percent"] = peak_profit

            should_close = False
            close_reason = "OPEN"

            activation = float(open_position.get("trailing_activation", 0.75))
            pullback = float(open_position.get("trailing_pullback", 0.35))
            stop_loss = float(open_position.get("adaptive_stop_loss", -0.5))

            if move_percent <= stop_loss:
                should_close = True
                close_reason = "REPLAY_ADAPTIVE_STOP_LOSS"

            elif peak_profit >= activation and move_percent <= peak_profit - pullback:
                should_close = True
                close_reason = "REPLAY_TRAILING_EXIT"

            elif signal in ["BUY", "SELL"] and signal != trade_signal:
                should_close = True
                close_reason = "REPLAY_OPPOSITE_SIGNAL"

            if should_close:
                trade = {
                    "strategy": open_position["strategy"],
                    "original_strategy": open_position.get("original_strategy"),
                    "signal": trade_signal,
                    "entry_price": round(entry_price, 3),
                    "exit_price": round(price, 3),
                    "return_percent": round(move_percent, 3),
                    "result": close_reason,
                    "confidence": open_position["confidence"],
                    "original_confidence": open_position.get("original_confidence"),
                    "replay_learning_adjustment": open_position.get(
                        "replay_learning_adjustment"
                    ),
                    "replay_learning_reasons": open_position.get(
                        "replay_learning_reasons"
                    ),
                    "support_resistance_adjustment": open_position.get(
                    "support_resistance_adjustment"
                ),
                    "support_resistance_reasons": open_position.get(
                        "support_resistance_reasons"

                    
                    ),
                    "learned_support_resistance_adjustment": open_position.get(
                        "learned_support_resistance_adjustment"
                    ),
                    "learned_support_resistance_reasons": open_position.get(
                        "learned_support_resistance_reasons"
                    ),
                    
                    "opened_at": open_position["opened_at"],
                    "closed_at": str(timestamp),
                    "atr_percent_at_entry": round(
                        open_position["atr_percent_at_entry"],
                        3
                    ),
                    "peak_profit_percent": round(peak_profit, 3),
                    "market_regime": open_position["market_regime"],
                    "volatility_regime": open_position["volatility_regime"],
                    "rotation_changed": open_position.get("rotation_changed", False),
                    "rotation_reason": open_position.get("rotation_reason"),
                    "strategy_reason": open_position.get("strategy_reason"),
                    "trailing_activation": open_position.get("trailing_activation"),
                    "trailing_pullback": open_position.get("trailing_pullback"),
                    "adaptive_stop_loss": open_position.get("adaptive_stop_loss"),
                    "rsi_at_entry": open_position.get("rsi_at_entry"),
                    "trade_quality_score": open_position.get("trade_quality_score"),
                    "trade_quality_label": open_position.get("trade_quality_label"),
                    "trade_quality_reasons": open_position.get("trade_quality_reasons"),
                    "trend_at_entry": open_position.get("trend_at_entry"),
                    
                    "support_resistance_status": open_position.get("support_resistance_status"),
                    "nearest_support": open_position.get("nearest_support"),
                    "nearest_resistance": open_position.get("nearest_resistance"),
                    "distance_to_support": open_position.get("distance_to_support"),
                    "distance_to_resistance": open_position.get("distance_to_resistance"),
                    "support_strength": open_position.get("support_strength"),
                    "resistance_strength": open_position.get("resistance_strength"),
                    
                    "close_at_entry": open_position.get("close_at_entry"),
                    "ma20_at_entry": open_position.get("ma20_at_entry"),
                    "ma50_at_entry": open_position.get("ma50_at_entry"),
                    "distance_ma20": open_position.get("distance_ma20"),
                    "distance_ma50": open_position.get("distance_ma50"),
                    "previous_candle_return": open_position.get(
                        "previous_candle_return"
                    ),
                    "trend_strength": open_position.get("trend_strength"),
                    "ma_alignment": open_position.get("ma_alignment"),
                    "rsi_slope": open_position.get("rsi_slope"),
                }

                save_replay_trade(trade)
                trades.append(trade)
                open_position = None

        previous_row = row

    if open_position is not None:
        final_row = df.iloc[-1]
        final_price = float(final_row["Close"])

        entry_price = float(open_position["entry_price"])
        trade_signal = open_position["signal"]

        move_percent = ((final_price - entry_price) / entry_price) * 100

        if trade_signal == "SELL":
            move_percent *= -1

        trade = {
            "strategy": open_position["strategy"],
            "original_strategy": open_position.get("original_strategy"),
            "signal": trade_signal,
            "entry_price": round(entry_price, 3),
            "exit_price": round(final_price, 3),
            "return_percent": round(move_percent, 3),
            "result": "REPLAY_END_FORCED_CLOSE",
            "confidence": open_position["confidence"],
            "original_confidence": open_position.get("original_confidence"),
            "replay_learning_adjustment": open_position.get("replay_learning_adjustment"),
            
            "support_resistance_adjustment": open_position.get(
            "support_resistance_adjustment"
        ),
           "support_resistance_reasons": open_position.get(
            "support_resistance_reasons"
        ),
        "learned_support_resistance_adjustment": open_position.get(
    "learned_support_resistance_adjustment"
),
"learned_support_resistance_reasons": open_position.get(
    "learned_support_resistance_reasons"
),
            "opened_at": open_position["opened_at"],
            "closed_at": str(df.index[-1]),
            "atr_percent_at_entry": round(open_position["atr_percent_at_entry"], 3),
            "peak_profit_percent": round(open_position.get("peak_profit_percent", 0), 3),
            "market_regime": open_position["market_regime"],
            "volatility_regime": open_position["volatility_regime"],
            "rotation_changed": open_position.get("rotation_changed", False),
            "rotation_reason": open_position.get("rotation_reason"),
            "strategy_reason": open_position.get("strategy_reason"),
            "trailing_activation": open_position.get("trailing_activation"),
            "trailing_pullback": open_position.get("trailing_pullback"),
            "adaptive_stop_loss": open_position.get("adaptive_stop_loss"),
            "rsi_at_entry": open_position.get("rsi_at_entry"),
            "trend_at_entry": open_position.get("trend_at_entry"),
            "risk_at_entry": open_position.get("risk_at_entry"),
            "trade_quality_score": open_position.get("trade_quality_score"),
            "trade_quality_label": open_position.get("trade_quality_label"),
            "trade_quality_reasons": open_position.get("trade_quality_reasons"),
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

        save_replay_trade(trade)
        trades.append(trade)
        open_position = None

    total_trades = len(trades)
    wins = len([t for t in trades if t["return_percent"] > 0])
    losses = len([t for t in trades if t["return_percent"] <= 0])

    win_rate = round((wins / total_trades) * 100, 2) if total_trades else 0

    average_return = round(
        sum(t["return_percent"] for t in trades) / total_trades,
        3
    ) if total_trades else 0

    control_result = record_replay_control_result(
        total_trades=total_trades,
        blocked_by_learning=blocked_by_learning,
        win_rate=win_rate,
        average_return=average_return
    )

    if entry_weights_override is None:
        entry_learning = update_entry_weights_after_replay(
            win_rate=win_rate,
            average_return=average_return
        )
    else:
        entry_learning = {
            "decision": "TEST_ONLY",
            "entry_weights": entry_weights_override,
            "note": "Replay used temporary entry weights. Entry memory was not updated."
        }

    return {
        "status": "completed",
        "mode": "ai_replay_sandbox_v2_learning_context",
        "period": period,
        "interval": interval,
        "candles_processed": len(df),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "average_return": average_return,
        "entry_learning": entry_learning,
        "blocked_by_learning": blocked_by_learning,
        "learning_controller": control_result,
        "output_file": REPLAY_TRADES_FILE,
        "note": "AI replay sandbox V2 completed with Stage 26 adaptive entry weight tuning support."
    }