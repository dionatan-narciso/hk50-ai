import os
import pandas as pd

FILE = "data/confidence_calibration.csv"


def get_confidence_bucket(confidence):
    confidence = float(confidence)

    if confidence < 55:
        return "UNDER_55"

    if confidence < 65:
        return "55_64"

    if confidence < 75:
        return "65_74"

    if confidence < 85:
        return "75_84"

    return "85_PLUS"


def update_confidence_calibration(confidence, trade_return):
    os.makedirs("data", exist_ok=True)

    bucket = get_confidence_bucket(confidence)

    if os.path.exists(FILE):
        df = pd.read_csv(FILE)
    else:
        df = pd.DataFrame(columns=[
            "confidence_bucket",
            "trades",
            "wins",
            "losses",
            "win_rate",
            "average_return",
        ])

    mask = df["confidence_bucket"] == bucket

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
        win_rate = round((wins / trades) * 100, 2)

        df.at[idx, "trades"] = trades
        df.at[idx, "wins"] = wins
        df.at[idx, "losses"] = losses
        df.at[idx, "win_rate"] = win_rate
        df.at[idx, "average_return"] = round(avg, 3)

    else:
        wins = 1 if trade_return > 0 else 0
        losses = 0 if trade_return > 0 else 1
        win_rate = round(wins * 100, 2)

        df.loc[len(df)] = {
            "confidence_bucket": bucket,
            "trades": 1,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "average_return": round(trade_return, 3),
        }

    df.to_csv(FILE, index=False)


def get_confidence_calibration_bonus(confidence):
    if not os.path.exists(FILE):
        return {
            "confidence_calibration_bonus": 0,
            "reason": "No confidence calibration data yet."
        }

    df = pd.read_csv(FILE)

    if df.empty:
        return {
            "confidence_calibration_bonus": 0,
            "reason": "Confidence calibration memory is empty."
        }

    bucket = get_confidence_bucket(confidence)
    match = df[df["confidence_bucket"] == bucket]

    if match.empty:
        return {
            "confidence_calibration_bonus": 0,
            "reason": f"No calibration history for confidence bucket {bucket}."
        }

    row = match.iloc[0]

    trades = int(row.get("trades", 0))
    win_rate = float(row.get("win_rate", 0))
    average_return = float(row.get("average_return", 0))

    if trades < 5:
        return {
            "confidence_calibration_bonus": 0,
            "reason": (
                f"Only {trades} trade(s) in confidence bucket {bucket}. "
                "Not enough calibration data yet."
            )
        }

    if win_rate >= 65 and average_return > 0:
        return {
            "confidence_calibration_bonus": 5,
            "reason": (
                f"Confidence bucket {bucket} is performing well. "
                f"Win rate {win_rate}%, average return {average_return}%."
            )
        }

    if win_rate < 45 or average_return < 0:
        return {
            "confidence_calibration_bonus": -7,
            "reason": (
                f"Confidence bucket {bucket} is underperforming. "
                f"Win rate {win_rate}%, average return {average_return}%."
            )
        }

    return {
        "confidence_calibration_bonus": 0,
        "reason": (
            f"Confidence bucket {bucket} is neutral. "
            f"Win rate {win_rate}%, average return {average_return}%."
        )
    }