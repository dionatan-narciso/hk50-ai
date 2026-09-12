from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.entry_context_scoring import calculate_entry_context_score
from app.historical_replay_engine import (
    build_market_snapshot,
    calculate_atr,
    calculate_rsi,
    get_adaptive_replay_settings,
    run_ai_replay_decision,
)
from app.oos_validation.engine import _load_replay_entry_weights, discovery_state_fingerprint
from app.oos_validation.forward_dataset import get_batch_paths
from app.oos_validation.repository import append_validation_trade, reset_validation_journal
from app.replay_higher_timeframe_context import derive_replay_higher_timeframe_context
from app.utils.trade_context import calculate_trade_context
from replay_penalty_engine import get_replay_penalty


def _load_batch(batch_id: str) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Path]]:
    paths = get_batch_paths(batch_id)
    if not paths["manifest"].exists() or not paths["dataset"].exists():
        raise FileNotFoundError(f"Frozen forward OOS dataset is missing for {batch_id}")

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if manifest.get("manifest_sha256") != expected:
        raise ValueError("Forward OOS manifest integrity check failed")
    dataset_sha = hashlib.sha256(paths["dataset"].read_bytes()).hexdigest()
    if dataset_sha != manifest.get("dataset_sha256"):
        raise ValueError("Forward OOS dataset integrity check failed")

    data = pd.read_csv(paths["dataset"], index_col="timestamp_utc", parse_dates=True)
    index = pd.to_datetime(data.index, utc=True, errors="coerce")
    if index.isna().any():
        raise ValueError("Forward OOS dataset contains invalid timestamps")
    data.index = index
    data = data.sort_index()
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(data.columns):
        raise ValueError("Forward OOS dataset is missing OHLC columns")

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["RSI"] = calculate_rsi(data["Close"])
    data["ATR"] = calculate_atr(data)
    data["ATR_PERCENT"] = (data["ATR"] / data["Close"]) * 100
    data = data.dropna(subset=["MA20", "MA50", "RSI", "ATR", "ATR_PERCENT"])
    return manifest, data, paths


def run_forward_batch_replay(batch_id: str) -> dict[str, Any]:
    """Reconstruct continuous OOS state and score only one immutable forward batch."""
    manifest, data, paths = _load_batch(batch_id)
    execution_start = pd.Timestamp(manifest["execution_start"])
    validation_start = pd.Timestamp(manifest["validation_window"]["start"])
    validation_end = pd.Timestamp(manifest["validation_window"]["end"])
    entry_weights = _load_replay_entry_weights()

    reset_validation_journal(paths["journal"])
    open_position = None
    scored_trades: list[dict[str, Any]] = []
    blocked_by_learning = 0
    previous_row = None

    for timestamp, row in data.iterrows():
        market_snapshot = build_market_snapshot(row, previous_row)
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
        in_execution = execution_start <= timestamp < validation_end
        in_scored = validation_start <= timestamp < validation_end

        if open_position is None and in_execution and signal in ["BUY", "SELL"]:
            penalty = get_replay_penalty(
                strategy=strategy,
                market_regime=market_regime,
                volatility_regime=volatility_regime,
                rotation_changed=rotation_changed,
            )
            trade_context = calculate_trade_context(market_snapshot)
            market_snapshot.update(trade_context)
            entry_score = calculate_entry_context_score(
                market_snapshot, entry_weights_override=entry_weights
            )
            adjustment = penalty.get("total_adjustment", 0)
            adjusted_confidence = max(
                0,
                min(
                    100,
                    confidence + adjustment + entry_score.get("entry_context_adjustment", 0),
                ),
            )
            if adjusted_confidence <= 55:
                if in_scored:
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
                "replay_learning_adjustment": adjustment,
                "replay_learning_reasons": " | ".join(penalty.get("reasons", [])),
                "entry_context_adjustment": entry_score.get("entry_context_adjustment", 0),
                "entry_context_reasons": " | ".join(entry_score.get("entry_context_reasons", [])),
                "rotation_changed": rotation_changed,
                "rotation_reason": decision.get("rotation_reason"),
                "strategy_reason": decision.get("reason"),
                "trailing_activation": settings["activation"],
                "trailing_pullback": settings["pullback"],
                "adaptive_stop_loss": settings["stop_loss"],
                "rsi_at_entry": market_snapshot.get("rsi"),
                "trend_at_entry": market_snapshot.get("trend"),
                "risk_at_entry": market_snapshot.get("risk"),
                **trade_context,
            }

        elif open_position is not None and in_execution:
            entry_price = float(open_position["entry_price"])
            trade_signal = open_position["signal"]
            move_percent = ((price - entry_price) / entry_price) * 100
            if trade_signal == "SELL":
                move_percent *= -1
            peak_profit = max(float(open_position.get("peak_profit_percent", 0)), move_percent)
            open_position["peak_profit_percent"] = peak_profit
            activation = float(open_position.get("trailing_activation", 0.75))
            pullback = float(open_position.get("trailing_pullback", 0.35))
            stop_loss = float(open_position.get("adaptive_stop_loss", -0.5))
            should_close = False
            close_reason = "OPEN"
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
                    "replay_learning_adjustment": open_position.get("replay_learning_adjustment"),
                    "replay_learning_reasons": open_position.get("replay_learning_reasons"),
                    "opened_at": open_position["opened_at"],
                    "closed_at": str(timestamp),
                    "atr_percent_at_entry": round(open_position["atr_percent_at_entry"], 3),
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
                    "trend_at_entry": open_position.get("trend_at_entry"),
                    "risk_at_entry": open_position.get("risk_at_entry"),
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
                if in_scored:
                    htf = derive_replay_higher_timeframe_context(
                        data[["Open", "High", "Low", "Close"]], trade["opened_at"]
                    )
                    trade.update(
                        {
                            "context_htf_trend_4h": htf.trend_4h,
                            "context_htf_trend_1d": htf.trend_1d,
                            "context_htf_agreement": htf.agreement,
                            "context_htf_aligned_direction": htf.aligned_direction or "UNKNOWN",
                        }
                    )
                    append_validation_trade(trade, paths["journal"])
                    scored_trades.append(trade)
                open_position = None

        previous_row = row

    returns = [float(trade["return_percent"]) for trade in scored_trades]
    wins = sum(value > 0 for value in returns)
    total = len(returns)
    return {
        "status": "completed",
        "mode": "forward_oos_batch_replay",
        "batch_id": batch_id,
        "candidate_snapshot_sha256": manifest["candidate_snapshot_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "execution_start": manifest["execution_start"],
        "validation_window": manifest["validation_window"],
        "candles_processed": int(((data.index >= validation_start) & (data.index < validation_end)).sum()),
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round((wins / total) * 100, 2) if total else 0.0,
        "average_return": round(sum(returns) / total, 3) if total else 0.0,
        "blocked_by_learning": blocked_by_learning,
        "open_position_at_end": open_position is not None,
        "discovery_state": discovery_state_fingerprint(),
        "output_file": str(paths["journal"]),
        "note": "Forward replay reconstructs continuous OOS state but scores only this batch.",
    }
