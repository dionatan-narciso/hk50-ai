import yfinance as yf
import pandas as pd
from datetime import datetime

from app.research.research_results_repository import (
    append_research_results,
    load_research_results,
)


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
    return {"strategies": results}


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
    return {"parameter_tests": results}


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
        backtest_evolution_strategy(df, rsi_entry, use_macd, use_trend)
        for rsi_entry, use_macd, use_trend in combinations
    ]

    results = sorted(results, key=lambda x: x["total_return"], reverse=True)

    for index, result in enumerate(results, start=1):
        result["rank"] = index

    save_research_results("Evolution Lab", results[:10])
    return {"evolution_tests": results[:10]}


def save_research_results(lab_type, results):
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

    append_research_results(rows)


def run_research_memory():
    df = load_research_results()

    if df is None:
        return {
            "best_strategy": None,
            "worst_strategy": None,
            "total_tests_saved": 0,
            "message": "No research memory saved yet.",
        }

    if df.empty:
        return {
            "best_strategy": None,
            "worst_strategy": None,
            "total_tests_saved": 0,
            "message": "Research memory file is empty.",
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

    return {"walk_forward_tests": results}
