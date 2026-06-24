import yfinance as yf
import pandas as pd
import os
from datetime import datetime
from app.trade_analytics import run_trade_analytics


def load_hk50_data():
    ticker = yf.Ticker("^HSI")
    df = ticker.history(period="1y", interval="1d")

    if df.empty:
        raise ValueError("No data returned from Yahoo Finance")

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA100"] = df["Close"].rolling(100).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()

    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["HIGH_20"] = df["Close"].rolling(20).max()
    df["LOW_20"] = df["Close"].rolling(20).min()

    return df.dropna()


def backtest_strategy(df, strategy_name):
    position_open = False
    entry_price = 0
    equity = 10000
    equity_curve = [equity]
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        previous = df.iloc[i - 1]

        buy_signal = False
        sell_signal = False

        if strategy_name == "MA20_MA50":
            buy_signal = previous["MA20"] <= previous["MA50"] and row["MA20"] > row["MA50"]
            sell_signal = previous["MA20"] >= previous["MA50"] and row["MA20"] < row["MA50"]

        elif strategy_name == "RSI Only":
            buy_signal = row["RSI"] < 35
            sell_signal = row["RSI"] > 60

        elif strategy_name == "MACD Only":
            buy_signal = previous["MACD"] <= previous["MACD_SIGNAL"] and row["MACD"] > row["MACD_SIGNAL"]
            sell_signal = previous["MACD"] >= previous["MACD_SIGNAL"] and row["MACD"] < row["MACD_SIGNAL"]

        elif strategy_name == "RSI + MACD":
            buy_signal = row["RSI"] < 45 and row["MACD"] > row["MACD_SIGNAL"]
            sell_signal = row["RSI"] > 60 or row["MACD"] < row["MACD_SIGNAL"]

        elif strategy_name == "Trend Following":
            buy_signal = row["Close"] > row["MA50"] and row["MA50"] > row["MA100"]
            sell_signal = row["Close"] < row["MA50"]

        elif strategy_name == "Breakout":
            buy_signal = row["Close"] > previous["HIGH_20"]
            sell_signal = row["Close"] < row["MA20"]

        elif strategy_name == "Mean Reversion":
            buy_signal = row["Close"] < row["LOW_20"] and row["RSI"] < 40
            sell_signal = row["Close"] > row["MA20"] or row["RSI"] > 60

        if not position_open and buy_signal:
            entry_price = row["Close"]
            position_open = True

        elif position_open and sell_signal:
            exit_price = row["Close"]
            trade_return = ((exit_price - entry_price) / entry_price) * 100
            trades.append(trade_return)

            equity = equity * (1 + trade_return / 100)
            equity_curve.append(equity)

            position_open = False

    total_trades = len(trades)
    wins = [trade for trade in trades if trade > 0]
    losses = [trade for trade in trades if trade < 0]

    total_return = round(((equity - 10000) / 10000) * 100, 2)
    win_rate = round((len(wins) / total_trades) * 100, 2) if total_trades else 0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss else 0

    average_trade = round(sum(trades) / total_trades, 2) if total_trades else 0
    best_trade = round(max(trades), 2) if trades else 0
    worst_trade = round(min(trades), 2) if trades else 0

    peak = equity_curve[0]
    max_drawdown = 0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = ((value - peak) / peak) * 100
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    max_drawdown = round(max_drawdown, 2)

    signal = "BUY" if total_return >= 0 else "SELL"

    return {
        "strategy": strategy_name,
        "trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "average_trade": average_trade,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "max_drawdown": max_drawdown,
        "signal": signal,
    }

def run_strategy_lab():
    df = load_hk50_data()

    strategies = [
        "MA20_MA50",
        "RSI Only",
        "MACD Only",
        "RSI + MACD",
        "Trend Following",
        "Breakout",
        "Mean Reversion",
    ]

    results = [backtest_strategy(df, strategy) for strategy in strategies]

    results = sorted(results, key=lambda x: x["total_return"], reverse=True)

    for index, result in enumerate(results, start=1):
        result["rank"] = index
    save_research_results("Strategy Lab", results)
    return {
        "strategies": results
    }

def backtest_rsi_parameter(df, rsi_entry):
    position_open = False
    entry_price = 0
    equity = 10000
    equity_curve = [equity]
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]

        buy_signal = row["RSI"] < rsi_entry
        sell_signal = row["RSI"] > 60

        if not position_open and buy_signal:
            entry_price = row["Close"]
            position_open = True

        elif position_open and sell_signal:
            exit_price = row["Close"]
            trade_return = ((exit_price - entry_price) / entry_price) * 100
            trades.append(trade_return)

            equity = equity * (1 + trade_return / 100)
            equity_curve.append(equity)

            position_open = False

    total_trades = len(trades)
    wins = [trade for trade in trades if trade > 0]
    losses = [trade for trade in trades if trade < 0]

    total_return = round(((equity - 10000) / 10000) * 100, 2)
    win_rate = round((len(wins) / total_trades) * 100, 2) if total_trades else 0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss else 0

    average_trade = round(sum(trades) / total_trades, 2) if total_trades else 0

    peak = equity_curve[0]
    max_drawdown = 0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = ((value - peak) / peak) * 100
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return {
        "parameter": f"RSI < {rsi_entry}",
        "rsi_entry": rsi_entry,
        "trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "average_trade": average_trade,
        "max_drawdown": round(max_drawdown, 2),
        "signal": "BUY" if total_return >= 0 else "SELL",
    }


def run_parameter_lab():
    df = load_hk50_data()

    rsi_values = [25, 30, 35, 40, 45, 50]

    results = [backtest_rsi_parameter(df, value) for value in rsi_values]

    results = sorted(results, key=lambda x: x["total_return"], reverse=True)

    for index, result in enumerate(results, start=1):
        result["rank"] = index

    save_research_results("Parameter Lab", results)

    return {
        "parameter_tests": results
    }

def backtest_evolution_strategy(df, rsi_entry, use_macd=False, use_trend=False):
    position_open = False
    entry_price = 0
    equity = 10000
    equity_curve = [equity]
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]

        buy_signal = row["RSI"] < rsi_entry
        sell_signal = row["RSI"] > 60

        if use_macd:
            buy_signal = buy_signal and row["MACD"] > row["MACD_SIGNAL"]
            sell_signal = sell_signal or row["MACD"] < row["MACD_SIGNAL"]

        if use_trend:
            buy_signal = buy_signal and row["Close"] > row["MA50"]
            sell_signal = sell_signal or row["Close"] < row["MA50"]

        if not position_open and buy_signal:
            entry_price = row["Close"]
            position_open = True

        elif position_open and sell_signal:
            exit_price = row["Close"]
            trade_return = ((exit_price - entry_price) / entry_price) * 100
            trades.append(trade_return)

            equity = equity * (1 + trade_return / 100)
            equity_curve.append(equity)

            position_open = False

    total_trades = len(trades)
    wins = [trade for trade in trades if trade > 0]
    losses = [trade for trade in trades if trade < 0]

    total_return = round(((equity - 10000) / 10000) * 100, 2)
    win_rate = round((len(wins) / total_trades) * 100, 2) if total_trades else 0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss else 0

    average_trade = round(sum(trades) / total_trades, 2) if total_trades else 0

    peak = equity_curve[0]
    max_drawdown = 0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = ((value - peak) / peak) * 100
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    name_parts = [f"RSI<{rsi_entry}"]

    if use_macd:
        name_parts.append("MACD")

    if use_trend:
        name_parts.append("Trend")

    strategy_name = " + ".join(name_parts)

    return {
        "strategy": strategy_name,
        "rsi_entry": rsi_entry,
        "use_macd": use_macd,
        "use_trend": use_trend,
        "trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "average_trade": average_trade,
        "max_drawdown": round(max_drawdown, 2),
        "signal": "BUY" if total_return >= 0 else "SELL",
    }


def run_evolution_lab():
    df = load_hk50_data()

    rsi_values = [25, 30, 35, 40, 45]

    combinations = []

    for rsi_value in rsi_values:
        combinations.append((rsi_value, False, False))
        combinations.append((rsi_value, True, False))
        combinations.append((rsi_value, False, True))
        combinations.append((rsi_value, True, True))

    results = [
        backtest_evolution_strategy(
            df,
            rsi_entry,
            use_macd,
            use_trend
        )
        for rsi_entry, use_macd, use_trend in combinations
    ]

    results = sorted(results, key=lambda x: x["total_return"], reverse=True)

    for index, result in enumerate(results, start=1):
        result["rank"] = index

    save_research_results("Evolution Lab", results[:10])

    return {
        "evolution_tests": results[:10]
    }

def save_research_results(lab_type, results):
    os.makedirs("data", exist_ok=True)

    file_path = "data/research_results.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []

    for item in results:
        rows.append({
            "timestamp": timestamp,
            "lab_type": lab_type,
            "rank": item.get("rank"),
            "strategy": item.get("strategy") or item.get("parameter"),
            "trades": item.get("trades"),
            "win_rate": item.get("win_rate"),
            "profit_factor": item.get("profit_factor"),
            "total_return": item.get("total_return"),
            "average_trade": item.get("average_trade"),
            "max_drawdown": item.get("max_drawdown"),
            "signal": item.get("signal"),
        })

    df = pd.DataFrame(rows)

    if os.path.exists(file_path):
        df.to_csv(file_path, mode="a", header=False, index=False)
    else:
        df.to_csv(file_path, index=False)


def run_research_memory():
    file_path = "data/research_results.csv"

    if not os.path.exists(file_path):
        return {
            "best_strategy": None,
            "worst_strategy": None,
            "total_tests_saved": 0,
            "message": "No research memory saved yet."
        }

    df = pd.read_csv(file_path)

    if df.empty:
        return {
            "best_strategy": None,
            "worst_strategy": None,
            "total_tests_saved": 0,
            "message": "Research memory file is empty."
        }

    best = df.sort_values("total_return", ascending=False).iloc[0]
    worst = df.sort_values("total_return", ascending=True).iloc[0]

    return {
        "total_tests_saved": int(len(df)),
        "best_strategy": {
            "strategy": best["strategy"],
            "lab_type": best["lab_type"],
            "return": round(float(best["total_return"]), 2),
            "drawdown": round(float(best["max_drawdown"]), 2),
            "win_rate": round(float(best["win_rate"]), 2),
        },
        "worst_strategy": {
            "strategy": worst["strategy"],
            "lab_type": worst["lab_type"],
            "return": round(float(worst["total_return"]), 2),
            "drawdown": round(float(worst["max_drawdown"]), 2),
            "win_rate": round(float(worst["win_rate"]), 2),
        },
    }

def walk_forward_test_strategy(df, strategy_name):
    split_index = int(len(df) * 0.7)

    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    train_result = backtest_strategy(train_df, strategy_name)
    test_result = backtest_strategy(test_df, strategy_name)

    train_return = train_result["total_return"]
    test_return = test_result["total_return"]

    if train_return > 0 and test_return > 0:
        robustness = "PASS"
        robustness_score = 90
    elif train_return > 0 and test_return <= 0:
        robustness = "FAIL"
        robustness_score = 35
    elif train_return <= 0 and test_return > 0:
        robustness = "UNSTABLE"
        robustness_score = 50
    else:
        robustness = "WEAK"
        robustness_score = 20

    return {
        "strategy": strategy_name,
        "train_return": train_return,
        "test_return": test_return,
        "train_trades": train_result["trades"],
        "test_trades": test_result["trades"],
        "train_drawdown": train_result["max_drawdown"],
        "test_drawdown": test_result["max_drawdown"],
        "robustness": robustness,
        "robustness_score": robustness_score,
    }


def run_walk_forward_lab():
    df = load_hk50_data()

    strategies = [
        "MA20_MA50",
        "RSI Only",
        "MACD Only",
        "RSI + MACD",
        "Trend Following",
        "Breakout",
        "Mean Reversion",
    ]

    results = [walk_forward_test_strategy(df, strategy) for strategy in strategies]

    results = sorted(results, key=lambda x: x["robustness_score"], reverse=True)

    for index, result in enumerate(results, start=1):
        result["rank"] = index

    return {
        "walk_forward_tests": results
    }

def run_research_director():
    strategy_lab = run_strategy_lab().get("strategies", [])
    parameter_lab = run_parameter_lab().get("parameter_tests", [])
    evolution_lab = run_evolution_lab().get("evolution_tests", [])
    walk_forward = run_walk_forward_lab().get("walk_forward_tests", [])
    memory = run_research_memory()

    analytics = run_trade_analytics()
    strategy_analytics = analytics.get("strategy_performance", [])

    memory_best_strategy = memory.get("best_strategy")
    worst_strategy = memory.get("worst_strategy")

    profitable_strategy_count = len([s for s in strategy_lab if s["total_return"] > 0])
    profitable_parameter_count = len([s for s in parameter_lab if s["total_return"] > 0])
    profitable_evolution_count = len([s for s in evolution_lab if s["total_return"] > 0])

    best_strategy_lab = strategy_lab[0] if strategy_lab else None
    best_parameter_lab = parameter_lab[0] if parameter_lab else None
    best_evolution_lab = evolution_lab[0] if evolution_lab else None
    best_walk_forward = walk_forward[0] if walk_forward else None

    live_performance = []
    live_score = 0
    best_live_strategy = None

    try:
        import pandas as pd

        live_df = pd.read_csv("data/live_strategy_performance.csv")
        live_performance = live_df.to_dict("records")

        if not live_df.empty:
            live_df = live_df.sort_values(
                by=["win_rate", "average_return", "total_trades"],
                ascending=False
            )

            best_live_strategy = live_df.iloc[0].to_dict()

            win_rate = float(best_live_strategy.get("win_rate", 0))
            avg_return = float(best_live_strategy.get("average_return", 0))
            total_trades = int(best_live_strategy.get("total_trades", 0))

            if total_trades >= 10 and win_rate >= 60 and avg_return > 0:
                live_score = 25
            elif total_trades >= 5 and win_rate >= 55 and avg_return > 0:
                live_score = 18
            elif total_trades >= 3 and avg_return > 0:
                live_score = 12
            elif total_trades >= 1 and avg_return > 0:
                live_score = 5

    except Exception:
        live_performance = []
        live_score = 0
        best_live_strategy = None

    strategy_candidates = []

    def get_analytics_bonus(strategy_name):
        for row in strategy_analytics:
            if row.get("strategy") == strategy_name:
                avg_return = float(row.get("average_return", 0))
                trades = int(row.get("trades", 0))

                if trades >= 5:
                    if avg_return > 0.5:
                        return 10
                    elif avg_return > 0:
                        return 5
                    elif avg_return < 0:
                        return -5

        return 0

    def add_candidate(strategy_name, source, research_score, live_bonus=0):
        if not strategy_name:
            return

        analytics_bonus = get_analytics_bonus(strategy_name)

        final_score = research_score + live_bonus + analytics_bonus

        strategy_candidates.append({
            "strategy": strategy_name,
            "source": source,
            "research_score": research_score,
            "live_bonus": live_bonus,
            "analytics_bonus": analytics_bonus,
            "final_score": final_score
        })

    if memory_best_strategy:
        add_candidate(
            strategy_name=(
                memory_best_strategy.get("strategy")
                if isinstance(memory_best_strategy, dict)
                else memory_best_strategy
            ),
            source="Research Memory",
            research_score=35,
            live_bonus=0
        )

    if best_strategy_lab:
        add_candidate(
            strategy_name=best_strategy_lab.get("strategy"),
            source="Strategy Lab",
            research_score=30,
            live_bonus=0
        )

    if best_parameter_lab:
        add_candidate(
            strategy_name=best_parameter_lab.get("parameter"),
            source="Parameter Lab",
            research_score=28,
            live_bonus=0
        )

    if best_evolution_lab:
        add_candidate(
            strategy_name=best_evolution_lab.get("strategy"),
            source="Evolution Lab",
            research_score=32,
            live_bonus=0
        )

    if best_walk_forward:
        robustness = best_walk_forward.get("robustness", "UNKNOWN")

        if robustness == "PASS":
            wf_score = 35
        elif robustness == "UNSTABLE":
            wf_score = 22
        elif robustness == "FAIL":
            wf_score = 10
        else:
            wf_score = 5

        add_candidate(
            strategy_name=best_walk_forward.get("strategy"),
            source="Walk Forward Lab",
            research_score=wf_score,
            live_bonus=0
        )

    if best_live_strategy:
        live_strategy_name = best_live_strategy.get("strategy")

        add_candidate(
            strategy_name=live_strategy_name,
            source="Live Performance Memory",
            research_score=20,
            live_bonus=live_score
        )

    if strategy_candidates:
        strategy_candidates = sorted(
            strategy_candidates,
            key=lambda x: x["final_score"],
            reverse=True
        )

        selected_strategy = strategy_candidates[0]
        best_strategy = selected_strategy["strategy"]

        if best_live_strategy:
            live_total_trades = int(best_live_strategy.get("total_trades", 0))
            live_win_rate = float(best_live_strategy.get("win_rate", 0))
            live_avg_return = float(best_live_strategy.get("average_return", 0))
            live_strategy_name = best_live_strategy.get("strategy")
            live_analytics_bonus = get_analytics_bonus(live_strategy_name)

            if (
                live_total_trades >= 10
                and live_win_rate >= 60
                and live_avg_return > 0
                and live_score >= 25
            ):
                selected_strategy = {
                    "strategy": live_strategy_name,
                    "source": "Live Performance Override",
                    "research_score": 20,
                    "live_bonus": live_score,
                    "analytics_bonus": live_analytics_bonus,
                    "final_score": 20 + live_score + live_analytics_bonus
                }

                best_strategy = live_strategy_name

    else:
        selected_strategy = None
        best_strategy = memory_best_strategy

    score = 0

    if best_strategy_lab:
        if best_strategy_lab["total_return"] > 3:
            score += 15
        elif best_strategy_lab["total_return"] > 1:
            score += 10
        elif best_strategy_lab["total_return"] > 0:
            score += 5

    if best_parameter_lab:
        if best_parameter_lab["total_return"] > 3:
            score += 15
        elif best_parameter_lab["total_return"] > 1:
            score += 10
        elif best_parameter_lab["total_return"] > 0:
            score += 5

    if best_evolution_lab:
        if best_evolution_lab["total_return"] > 3:
            score += 15
        elif best_evolution_lab["total_return"] > 1:
            score += 10
        elif best_evolution_lab["total_return"] > 0:
            score += 5

    if best_walk_forward:
        if best_walk_forward["robustness"] == "PASS":
            score += 25
        elif best_walk_forward["robustness"] == "UNSTABLE":
            score += 12
        elif best_walk_forward["robustness"] == "FAIL":
            score += 6
        else:
            score += 2

    tests_saved = memory.get("total_tests_saved", 0)

    if tests_saved >= 200:
        score += 10
    elif tests_saved >= 100:
        score += 7
    elif tests_saved >= 50:
        score += 5
    elif tests_saved >= 20:
        score += 3

    score += live_score

    confidence_score = min(score, 100)

    if confidence_score >= 80:
        confidence_label = "Strong"
    elif confidence_score >= 60:
        confidence_label = "Moderate"
    elif confidence_score >= 40:
        confidence_label = "Weak"
    else:
        confidence_label = "Very Weak"

    recommendations = []

    if selected_strategy:
        recommendations.append(
            f"Research Director selected {selected_strategy['strategy']} from "
            f"{selected_strategy['source']} with final score "
            f"{selected_strategy['final_score']}."
        )

    if selected_strategy and selected_strategy["source"] == "Live Performance Override":
        recommendations.append(
            "Live performance has enough evidence to override research memory."
        )

    if best_parameter_lab:
        recommendations.append(
            f"Best parameter result is {best_parameter_lab['parameter']} "
            f"with {best_parameter_lab['total_return']}% return."
        )

    if best_evolution_lab:
        recommendations.append(
            f"Best evolved strategy is {best_evolution_lab['strategy']} "
            f"with {best_evolution_lab['total_return']}% return."
        )

    if best_walk_forward:
        recommendations.append(
            f"Most robust walk forward result is {best_walk_forward['strategy']} "
            f"with status {best_walk_forward['robustness']}."
        )

    if best_live_strategy:
        recommendations.append(
            f"Live paper memory favours {best_live_strategy['strategy']} "
            f"with {best_live_strategy['win_rate']}% win rate and "
            f"{best_live_strategy['average_return']}% average return."
        )

    if worst_strategy:
        recommendations.append(
            f"Avoid or redesign {worst_strategy['strategy']} because it has "
            "the weakest saved result."
        )

    if confidence_score < 60:
        recommendations.append(
            "Research confidence is not strong enough yet. Focus on robustness "
            "and live paper performance before trusting live signals."
        )

    return {
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "profitable_strategy_count": profitable_strategy_count,
        "profitable_parameter_count": profitable_parameter_count,
        "profitable_evolution_count": profitable_evolution_count,

        "best_strategy": best_strategy,
        "selected_strategy": selected_strategy,
        "strategy_candidates": strategy_candidates,

        "worst_strategy": worst_strategy,
        "best_strategy_lab": best_strategy_lab,
        "best_parameter_lab": best_parameter_lab,
        "best_evolution_lab": best_evolution_lab,
        "most_robust": best_walk_forward,

        "live_score": live_score,
        "best_live_strategy": best_live_strategy,
        "live_performance": live_performance,

        "recommendations": recommendations,
    }

def save_trade_journal_entry(
    strategy,
    direction,
    entry_price,
    exit_price,
    notes="",
    confidence=None,
    vote_signal=None,
    vote_strength=None,
    total_votes=None,
    raw_signal=None,
    final_signal=None,
    result=None
):
    os.makedirs("data", exist_ok=True)

    file_path = "data/trade_journal.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)

    trade = {
        "timestamp": timestamp,
        "strategy": strategy,
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "result_pct": result_pct,
        "result": result or ("WIN" if result_pct > 0 else "LOSS"),
        "confidence": confidence,
        "vote_signal": vote_signal,
        "vote_strength": vote_strength,
        "total_votes": total_votes,
        "raw_signal": raw_signal,
        "final_signal": final_signal,
        "notes": notes,
    }

    df = pd.DataFrame([trade])

    if os.path.exists(file_path):
        existing = pd.read_csv(file_path)

        for column in trade.keys():
            if column not in existing.columns:
                existing[column] = ""

        existing = pd.concat([existing, df], ignore_index=True)
        existing.to_csv(file_path, index=False)

    else:
        df.to_csv(file_path, index=False)

    return trade

def run_trade_journal():
    file_path = "data/trade_journal.csv"

    if not os.path.exists(file_path):
        return {
            "total_trades": 0,
            "win_rate": 0,
            "average_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "trades": [],
        }

    df = pd.read_csv(file_path)

    if df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "average_return": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "trades": [],
        }

    wins = df[df["result_pct"] > 0]

    return {
        "total_trades": int(len(df)),
        "win_rate": round((len(wins) / len(df)) * 100, 2),
        "average_return": round(float(df["result_pct"].mean()), 2),
        "best_trade": round(float(df["result_pct"].max()), 2),
        "worst_trade": round(float(df["result_pct"].min()), 2),
        "trades": df.tail(10).to_dict(orient="records"),
    }

def run_live_learning_feed():
    trade_data = run_trade_journal()
    director = run_research_director()

    feed = []

    best_strategy = director.get("best_strategy")
    most_robust = director.get("most_robust")

    if best_strategy:
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Research",
            "signal": "BUY" if best_strategy["return"] >= 0 else "SELL",
            "strategy": best_strategy["strategy"],
            "result": f"{best_strategy['return']}%",
            "confidence": f"{director.get('confidence_score', 0)}%",
        })

    if most_robust:
        feed.append({
            "time": datetime.now().strftime("%H:%M"),
            "source": "Walk Forward",
            "signal": most_robust["robustness"],
            "strategy": most_robust["strategy"],
            "result": f"{most_robust['test_return']}%",
            "confidence": f"{most_robust['robustness_score']}%",
        })

    for trade in trade_data.get("trades", [])[-5:]:
        feed.append({
            "time": str(trade.get("timestamp", ""))[-8:],
            "source": "Paper Trade",
            "signal": trade.get("direction", "LONG"),
            "strategy": trade.get("strategy", ""),
            "result": f"{trade.get('result_pct', 0)}%",
            "confidence": "Tracked",
        })

    return {
        "feed": feed[:8]
    }