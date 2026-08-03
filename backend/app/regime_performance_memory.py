from pathlib import Path

import pandas as pd

from app.runtime_paths import RUNTIME_PATHS


COLUMNS = [
    "strategy",
    "market_regime",
    "volatility_regime",
    "trades",
    "wins",
    "losses",
    "average_return",
]


def get_regime_performance_path() -> Path:
    return RUNTIME_PATHS.paper_regime_performance_memory


def load_regime_performance() -> pd.DataFrame:
    path = get_regime_performance_path()
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path)


def update_regime_memory(
    strategy,
    market_regime,
    volatility_regime,
    trade_return,
):
    path = get_regime_performance_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    df = load_regime_performance()

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

    df.to_csv(path, index=False)
