import os
import pandas as pd

FILE = "data/regime_performance.csv"


def update_regime_memory(
    strategy,
    market_regime,
    volatility_regime,
    trade_return,
):
    os.makedirs("data", exist_ok=True)

    if os.path.exists(FILE):
        df = pd.read_csv(FILE)
    else:
        df = pd.DataFrame(columns=[
            "strategy",
            "market_regime",
            "volatility_regime",
            "trades",
            "wins",
            "losses",
            "average_return",
        ])

    mask = (
        (df["strategy"] == strategy)
        & (df["market_regime"] == market_regime)
        & (df["volatility_regime"] == volatility_regime)
    )

    if mask.any():
        idx = df[mask].index[0]

        trades = int(df.at[idx, "trades"]) + 1
        wins = int(df.at[idx, "wins"])
        losses = int(df.at[idx, "losses"])
        avg = float(df.at[idx, "average_return"])

        if trade_return > 0:
            wins += 1
        else:
            losses += 1

        avg = ((avg * (trades - 1)) + trade_return) / trades

        df.at[idx, "trades"] = trades
        df.at[idx, "wins"] = wins
        df.at[idx, "losses"] = losses
        df.at[idx, "average_return"] = round(avg, 3)

    else:
        df.loc[len(df)] = {
            "strategy": strategy,
            "market_regime": market_regime,
            "volatility_regime": volatility_regime,
            "trades": 1,
            "wins": 1 if trade_return > 0 else 0,
            "losses": 0 if trade_return > 0 else 1,
            "average_return": round(trade_return, 3),
        }

    df.to_csv(FILE, index=False)