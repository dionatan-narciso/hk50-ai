from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from app.trade_analytics import run_trade_analytics

from app.position_sizing_engine import calculate_position_size
from app.open_position_manager import get_open_position_status
from app.equity_curve import run_equity_curve

from app.live_performance_memory import (
    get_live_performance_memory_response,
    summarise_live_strategy_performance,
    update_live_strategy_memory,
)

from app.automatic_signal_tracker import (
    run_automatic_signal_tracker,
    save_open_position,
    clear_open_position,
    load_open_position
)

from app.voting_performance_memory import (
    summarise_voting_performance,
    save_voting_result
)

from app.research.director import run_research_director

from app.paper_trade_journal_repository import (
    save_trade_journal_entry,
    run_trade_journal,
    run_live_learning_feed as run_canonical_live_learning_feed,
)

from app.live_signal_engine import generate_live_signal

from app.quality_performance_memory import (
    get_quality_performance_summary,
    get_quality_analytics_bonus
)

from app.historical_replay_engine import run_historical_replay
from app.historical_replay_summary import get_historical_replay_summary
from replay_analytics import get_replay_analytics
from replay_learning_memory import build_replay_learning_memory
from replay_penalty_engine import get_replay_penalty
from replay_exit_analysis import analyze_replay_exits
from replay_exit_reason_analysis import analyze_replay_exit_reasons
from replay_winner_loser_analysis import analyze_winners_vs_losers
from app.trade_context_analytics import get_trade_context_analytics

from app.adaptive_entry_weight_tuner import tune_entry_weights


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/replay-penalty-test")
def replay_penalty_test(
    strategy: str = "RSI < 30",
    market_regime: str = "LOW_VOLATILITY",
    volatility_regime: str = "LOW_VOLATILITY",
    rotation_changed: bool = False
):
    return get_replay_penalty(
        strategy=strategy,
        market_regime=market_regime,
        volatility_regime=volatility_regime,
        rotation_changed=rotation_changed
    )


@app.get("/api/replay-exit-reason-analysis")
def replay_exit_reason_analysis():
    return analyze_replay_exit_reasons()


@app.get("/api/adaptive-entry-weight-tuner")
def adaptive_entry_weight_tuner():
    return tune_entry_weights(run_historical_replay)


@app.get("/api/replay-winner-loser-analysis")
def replay_winner_loser_analysis():
    return analyze_winners_vs_losers()


@app.get("/api/trade-context-analytics")
def trade_context_analytics():
    return get_trade_context_analytics()


@app.get("/api/replay-exit-analysis")
def replay_exit_analysis():
    return analyze_replay_exits()


@app.get("/api/build-replay-learning-memory")
def build_replay_memory():
    return build_replay_learning_memory()


@app.get("/api/replay-analytics")
def replay_analytics():
    return get_replay_analytics()


@app.get("/api/historical-replay-summary")
def historical_replay_summary():
    return get_historical_replay_summary()


@app.get("/api/historical-replay")
def historical_replay():
    return run_historical_replay(period="1y", interval="1h")


@app.get("/")
def home():
    return {"message": "HK50 AI Backend is running"}


@app.get("/api/trade-analytics")
def trade_analytics():
    return run_trade_analytics()


@app.get("/api/market-summary")
def market_summary():
    try:
        import yfinance as yf
        import pandas as pd
        from ta.momentum import RSIIndicator
        from ta.volatility import AverageTrueRange

        ticker = yf.Ticker("^HSI")
        data = ticker.history(period="90d", interval="1d")

        if data.empty or len(data) < 60:
            raise ValueError("Not enough market data returned")

        close = data["Close"]
        high = data["High"]
        low = data["Low"]

        latest = data.iloc[-1]
        previous = data.iloc[-2]

        current_price = round(latest["Close"], 2)
        change = round(current_price - previous["Close"], 2)
        percent = round((change / previous["Close"]) * 100, 2)

        ma20 = round(close.rolling(20).mean().iloc[-1], 2)
        ma50 = round(close.rolling(50).mean().iloc[-1], 2)

        rsi = round(RSIIndicator(close=close, window=14).rsi().iloc[-1], 2)

        atr = round(
            AverageTrueRange(high=high, low=low, close=close, window=14)
            .average_true_range()
            .iloc[-1],
            2,
        )

        atr_percent = round((atr / current_price) * 100, 2)

        trend = "Bullish" if current_price > ma20 > ma50 else "Bearish"

        trend_score = 70 if trend == "Bullish" else 40
        rsi_score = 70 if 45 <= rsi <= 65 else 50
        risk_score = 70 if atr_percent < 1.2 else 55

        confidence = round((trend_score + rsi_score + risk_score) / 3)

        risk = "Low" if atr_percent < 0.8 else "Medium" if atr_percent < 1.5 else "High"

        return {
            "price": f"{current_price:,.2f}",
            "change": f"{change:+.2f} ({percent:+.2f}%)",
            "trend": trend,
            "trend_detail": f"MA20 {ma20:,.2f} | MA50 {ma50:,.2f}",
            "confidence": confidence,
            "confidence_label": "Strong" if confidence >= 65 else "Moderate",
            "alignment": "Bullish Alignment" if trend == "Bullish" else "Bearish Alignment",
            "alignment_detail": "Live MA + RSI analysis",
            "alignment_score": trend_score,
            "risk": risk,
            "risk_detail": f"ATR: {atr_percent:.2f}%",
            "risk_score": risk_score,
            "market_status": "OPEN",
            "last_update": "Live",
            "auto_refresh": "30s",
            "rsi": rsi,
            "ma20": f"{ma20:,.2f}",
            "ma50": f"{ma50:,.2f}",
            "atr_percent": atr_percent,
        }

    except Exception as e:
        return {
            "price": "26,393.71",
            "change": "-2.90 (-0.01%)",
            "trend": "Bearish",
            "trend_detail": f"Fallback data active: {str(e)}",
            "confidence": 50,
            "confidence_label": "Moderate",
            "alignment": "Mixed Alignment",
            "alignment_detail": "Fallback analysis",
            "alignment_score": 50,
            "risk": "Medium",
            "risk_detail": "ATR: unavailable",
            "risk_score": 55,
            "market_status": "OPEN",
            "last_update": "Fallback",
            "auto_refresh": "30s",
        }


@app.get("/api/candles")
def get_candles():
    try:
        import yfinance as yf

        ticker = yf.Ticker("^HSI")
        data = ticker.history(period="30d", interval="1h")

        if data.empty:
            raise ValueError("No candle data returned")

        candles = []

        for index, row in data.tail(80).iterrows():
            candles.append({
                "time": index.strftime("%Y-%m-%d %H:%M"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]) if row["Volume"] else 0,
            })

        return {"candles": candles}

    except Exception as e:
        return {
            "error": str(e),
            "candles": []
        }


@app.get("/api/strategy-lab")
def strategy_lab():
    return run_strategy_lab()


@app.get("/api/parameter-lab")
def parameter_lab():
    return run_parameter_lab()


@app.get("/api/evolution-lab")
def evolution_lab():
    return run_evolution_lab()


@app.get("/api/research-memory")
def research_memory():
    return run_research_memory()


@app.get("/api/walk-forward-lab")
def walk_forward_lab():
    return run_walk_forward_lab()


@app.get("/api/research-director")
def research_director():
    return run_research_director()


@app.get("/api/trade-journal")
def trade_journal():
    return run_trade_journal()


@app.post("/api/trade-journal/add")
def add_trade_journal_entry(
    strategy: str,
    direction: str,
    entry_price: float,
    exit_price: float,
    notes: str = ""
):
    return save_trade_journal_entry(
        strategy=strategy,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        notes=notes
    )


@app.get("/api/live-learning-feed")
def live_learning_feed():
    return run_canonical_live_learning_feed(run_research_director)


@app.get("/api/automatic-signal-tracker")
def automatic_signal_tracker():
    market_data = market_summary()
    live_signal = generate_live_signal(market_data)

    current_price = float(str(market_data.get("price", 0)).replace(",", ""))
    atr_percent = market_data.get("atr_percent", 1.5)

    tracker_result = run_automatic_signal_tracker(
        symbol="HK50",
        current_price=current_price,
        signal=live_signal.get("signal", "HOLD"),
        confidence=live_signal.get("confidence", 50),
        reason=live_signal.get("reason", "No reason provided"),
        save_trade_function=lambda trade: trade,
        atr_percent=atr_percent,
        vote_signal=live_signal.get("vote_signal", "UNKNOWN"),
        vote_strength=live_signal.get("vote_strength", 0),
        total_votes=live_signal.get("total_votes", 0),
        raw_signal=live_signal.get("raw_signal")
        or live_signal.get("raw_strategy_signal", "UNKNOWN"),
        quality=ai_execution_engine().get("position_size", {}).get("quality", "UNKNOWN"),
    )

    return {
        "market_data": market_data,
        "live_signal": live_signal,
        "tracker_result": tracker_result
    }


@app.get("/api/ai-execution-engine")
def ai_execution_engine():
    market_data = market_summary()
    live_signal = generate_live_signal(market_data)

    research_director_data = run_research_director()

    open_position_data = load_open_position()

    position_size = calculate_position_size(
        confidence=live_signal.get("confidence", 0),
        risk=market_data.get("risk", "Medium"),
        live_score=research_director_data.get("live_score", 0),
        robustness=(
            research_director_data.get("most_robust", {}) or {}
        ).get("robustness", "UNKNOWN")
    )

    tracker_status = {
        "open_position": "NONE",
        "tracker_status": "IDLE"
    }

    if open_position_data:
        tracker_status["open_position"] = (
            f'{open_position_data["signal"]} @ '
            f'{open_position_data["entry_price"]}'
        )
        tracker_status["tracker_status"] = "ACTIVE"

    return {
        "strategy": live_signal.get("strategy_used"),
        "raw_signal": live_signal.get("raw_strategy_signal"),
        "final_signal": live_signal.get("signal"),
        "confidence": live_signal.get("confidence"),
        "market_confidence": live_signal.get("market_confidence"),
        "research_confidence": live_signal.get("director_confidence"),
        "position_size": position_size,
        "quality": live_signal.get(
            "quality",
            position_size.get("quality", "UNKNOWN")
        ),
        "quality_analytics_bonus": live_signal.get(
            "quality_analytics_bonus",
            0
        ),
        "quality_analytics_reason": live_signal.get(
            "quality_analytics_reason",
            "No quality learning data yet"
        ),
        "strategy_performance_bonus": live_signal.get(
            "strategy_performance_bonus",
            0
        ),
        "strategy_performance_reason": live_signal.get(
            "strategy_performance_reason",
            "No strategy performance data yet"
        ),
        "reason": live_signal.get("reason"),
        "market_regime": live_signal.get("market_regime"),
        "volatility_regime": live_signal.get("volatility_regime"),
        "preferred_strategies": live_signal.get("preferred_strategies", []),
        "blocked_strategies": live_signal.get("blocked_strategies", []),
        "regime_bonus": live_signal.get("regime_bonus", 0),
        "regime_bonus_reason": live_signal.get("regime_bonus_reason"),
        "rotation_selected_strategy": live_signal.get("rotation_selected_strategy"),
        "rotation_original_strategy": live_signal.get("rotation_original_strategy"),
        "rotation_changed_strategy": live_signal.get("rotation_changed_strategy"),
        "rotation_reason": live_signal.get("rotation_reason"),
        "rotation_scores": live_signal.get("rotation_scores", []),
        "open_position": tracker_status["open_position"],
        "tracker_status": tracker_status["tracker_status"],
        "trade_analytics_reason": live_signal.get(
            "trade_analytics_reason",
            "Not available"
        ),
        "strategy_vote": live_signal.get(
            "strategy_vote",
            {}
        ),
        "vote_signal": live_signal.get(
            "vote_signal",
            "UNKNOWN"
        ),
        "vote_strength": live_signal.get(
            "vote_strength",
            0
        ),
        "total_votes": live_signal.get(
            "total_votes",
            0
        ),
        "voting_assist_reason": live_signal.get(
            "voting_assist_reason",
            "Not available"
        ),
        "peak_profit_percent": (
            open_position_data.get("peak_profit_percent", 0)
            if open_position_data
            else 0
        ),
        "trailing_active": (
            open_position_data.get("trailing_active", False)
            if open_position_data
            else False
        ),
    }


@app.get("/api/live-performance-memory")
def live_performance_memory():
    return get_live_performance_memory_response()

@app.get("/api/test-live-memory")
def test_live_memory():
    from app.live_performance_memory import update_live_strategy_memory

    update_live_strategy_memory(
        strategy_name="RSI<30",
        trade_return=0.55
    )

    return {
        "message": "Live memory test saved",
        "strategy": "RSI<30",
        "return": 0.55
    }


@app.get("/api/open-position")
def open_position():
    market_data = market_summary()
    current_price = float(str(market_data.get("price", 0)).replace(",", ""))

    research_director_data = run_research_director()

    position_size = calculate_position_size(
        confidence=research_director_data.get("confidence_score", 0),
        risk=market_data.get("risk", "Medium"),
        live_score=research_director_data.get("live_score", 0),
        robustness=(
            research_director_data.get("most_robust", {}) or {}
        ).get("robustness", "UNKNOWN")
    )

    return get_open_position_status(
        current_price=current_price,
        position_size=position_size.get("position_size_label")
    )


@app.get("/api/equity-curve")
def equity_curve():
    return run_equity_curve()


@app.get("/api/voting-performance-memory")
def voting_performance_memory():
    return summarise_voting_performance()


@app.get("/api/live-strategy-performance")
def live_strategy_performance():
    return summarise_live_strategy_performance()


@app.get("/api/test-open-buy")
def test_open_buy():
    market_data = market_summary()
    current_price = float(str(market_data.get("price", 0)).replace(",", ""))

    position = {
        "symbol": "HK50",
        "entry_price": current_price,
        "signal": "BUY",
        "confidence": 70,
        "reason": "Manual Test",
        "vote_signal": "BUY",
        "vote_strength": 4,
        "total_votes": 4,
        "raw_signal": "BUY",
        "peak_profit_percent": 0,
        "trailing_active": False,
        "trailing_activation": 0.75,
        "trailing_pullback": 0.35,
        "atr_percent_at_entry": market_data.get("atr_percent", 1.5),
        "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_open_position(position)

    return {
        "status": "opened",
        "position": position
    }


@app.get("/api/test-open-sell")
def test_open_sell():
    market_data = market_summary()
    current_price = float(str(market_data.get("price", 0)).replace(",", ""))

    position = {
        "symbol": "HK50",
        "entry_price": current_price,
        "signal": "SELL",
        "confidence": 70,
        "reason": "Manual Test",
        "vote_signal": "SELL",
        "vote_strength": 4,
        "total_votes": 4,
        "raw_signal": "SELL",
        "peak_profit_percent": 0,
        "trailing_active": False,
        "trailing_activation": 0.75,
        "trailing_pullback": 0.35,
        "atr_percent_at_entry": market_data.get("atr_percent", 1.5),
        "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_open_position(position)

    return {
        "status": "opened",
        "position": position
    }


@app.get("/api/test-close-position")
def test_close_position():
    open_position = load_open_position()

    if not open_position:
        return {
            "status": "no_position",
            "message": "No open position to close"
        }

    market_data = market_summary()
    current_price = float(str(market_data.get("price", 0)).replace(",", ""))

    entry_price = float(open_position["entry_price"])
    trade_signal = open_position["signal"]

    move_percent = ((current_price - entry_price) / entry_price) * 100

    if trade_signal == "SELL":
        move_percent = move_percent * -1

    closed_trade = {
        "symbol": open_position["symbol"],
        "signal": trade_signal,
        "entry_price": entry_price,
        "exit_price": current_price,
        "return_percent": round(move_percent, 3),
        "result": "MANUAL_TEST_CLOSE",
        "confidence": open_position["confidence"],
        "reason": open_position["reason"],
        "vote_signal": open_position.get("vote_signal", "UNKNOWN"),
        "vote_strength": int(open_position.get("vote_strength", 0)),
        "total_votes": int(open_position.get("total_votes", 0)),
        "raw_signal": open_position.get("raw_signal", "UNKNOWN"),
        "opened_at": open_position["opened_at"],
        "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_trade_journal_entry(
        strategy=closed_trade.get("reason", "Manual Test"),
        direction=closed_trade["signal"],
        entry_price=closed_trade["entry_price"],
        exit_price=closed_trade["exit_price"],
        confidence=closed_trade.get("confidence"),
        vote_signal=closed_trade.get("vote_signal"),
        vote_strength=closed_trade.get("vote_strength"),
        total_votes=closed_trade.get("total_votes"),
        raw_signal=closed_trade.get("raw_signal"),
        final_signal=closed_trade.get("signal"),
        result=closed_trade.get("result"),
        notes="Manual test close"
    )

    update_live_strategy_memory(
        strategy_name=closed_trade.get("reason", "Manual Test"),
        trade_return=closed_trade["return_percent"]
    )

    save_voting_result(
        vote_signal=closed_trade.get("vote_signal", "UNKNOWN"),
        vote_strength=closed_trade.get("vote_strength", 0),
        total_votes=closed_trade.get("total_votes", 0),
        strategy_signal=closed_trade.get("raw_signal", "UNKNOWN"),
        final_signal=closed_trade.get("signal", "UNKNOWN"),
        trade_result=closed_trade["return_percent"]
    )

    clear_open_position()

    return {
        "status": "closed",
        "trade": closed_trade
    }


@app.get("/api/test-reset-position")
def test_reset_position():
    clear_open_position()

    return {
        "status": "reset",
        "message": "Open test position cleared"
    }


@app.get("/api/test-simulate-price")
def test_simulate_price(price: float = Query(...)):
    open_position = load_open_position()

    if not open_position:
        return {
            "status": "no_position",
            "message": "No open position to simulate"
        }

    entry_price = float(open_position["entry_price"])
    trade_signal = open_position["signal"]

    move_percent = ((price - entry_price) / entry_price) * 100

    if trade_signal == "SELL":
        move_percent = move_percent * -1

    peak_profit_percent = float(
        open_position.get("peak_profit_percent", 0)
    )

    trailing_active = str(
        open_position.get("trailing_active", False)
    ) == "True"

    if move_percent > peak_profit_percent:
        peak_profit_percent = round(move_percent, 3)
        open_position["peak_profit_percent"] = peak_profit_percent

    if move_percent >= 0.5:
        trailing_active = True
        open_position["trailing_active"] = True

    should_close = False
    result = "OPEN"

    if move_percent <= -0.3:
        should_close = True
        result = "LOSS_STOP"

    elif trailing_active and move_percent <= peak_profit_percent - 0.25:
        should_close = True
        result = "TRAILING_PROFIT_EXIT"

    if should_close:
        closed_trade = {
            "symbol": open_position["symbol"],
            "signal": trade_signal,
            "entry_price": entry_price,
            "exit_price": price,
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
            "opened_at": open_position["opened_at"],
            "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        save_trade_journal_entry(
            strategy=closed_trade.get("reason", "Manual Test"),
            direction=closed_trade["signal"],
            entry_price=closed_trade["entry_price"],
            exit_price=closed_trade["exit_price"],
            confidence=closed_trade.get("confidence"),
            vote_signal=closed_trade.get("vote_signal"),
            vote_strength=closed_trade.get("vote_strength"),
            total_votes=closed_trade.get("total_votes"),
            raw_signal=closed_trade.get("raw_signal"),
            final_signal=closed_trade.get("signal"),
            result=closed_trade.get("result"),
            notes="Simulated trailing close"
        )

        update_live_strategy_memory(
            strategy_name=closed_trade.get("reason", "Manual Test"),
            trade_return=closed_trade["return_percent"]
        )

        save_voting_result(
            vote_signal=closed_trade.get("vote_signal", "UNKNOWN"),
            vote_strength=closed_trade.get("vote_strength", 0),
            total_votes=closed_trade.get("total_votes", 0),
            strategy_signal=closed_trade.get("raw_signal", "UNKNOWN"),
            final_signal=closed_trade.get("signal", "UNKNOWN"),
            trade_result=closed_trade["return_percent"]
        )

        clear_open_position()

        return {
            "status": "closed",
            "reason": result,
            "trade": closed_trade
        }

    save_open_position(open_position)

    return {
        "status": "tracking",
        "entry_price": entry_price,
        "simulated_price": price,
        "signal": trade_signal,
        "move_percent": round(move_percent, 3),
        "peak_profit_percent": peak_profit_percent,
        "trailing_active": trailing_active,
        "position": open_position
    }


@app.get("/api/quality-performance-summary")
def quality_performance_summary():
    summary = get_quality_performance_summary()

    return {
        "summary": summary,
        "weak_bonus": get_quality_analytics_bonus("WEAK"),
        "moderate_bonus": get_quality_analytics_bonus("MODERATE"),
        "strong_bonus": get_quality_analytics_bonus("STRONG"),
        "exceptional_bonus": get_quality_analytics_bonus("EXCEPTIONAL")
    }
