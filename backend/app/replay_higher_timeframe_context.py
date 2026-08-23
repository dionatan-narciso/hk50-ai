from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.market_context.trends import normalize_trend


@dataclass(frozen=True)
class ReplayHigherTimeframeContext:
    """Leak-free higher-timeframe trend context for one replay entry."""

    trend_4h: str
    trend_1d: str
    agreement: str
    aligned_direction: str | None


def _completed_resample(history: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample already-closed lower-timeframe candles into completed bars only."""
    if history.empty:
        return pd.DataFrame()

    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(history.columns):
        return pd.DataFrame()

    result = history.resample(rule, label="right", closed="right").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        }
    )
    return result.dropna()


def _trend_from_resampled(resampled: pd.DataFrame) -> str:
    """Derive trend from the latest completed higher-timeframe bar."""
    if len(resampled) < 50:
        return "Neutral"

    close = resampled["Close"].astype(float)
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()

    latest_close = float(close.iloc[-1])
    latest_ma20 = float(ma20.iloc[-1])
    latest_ma50 = float(ma50.iloc[-1])

    if latest_close > latest_ma20 > latest_ma50:
        return "Bullish"
    if latest_close < latest_ma20 < latest_ma50:
        return "Bearish"
    return "Neutral"


def derive_replay_higher_timeframe_context(
    history: pd.DataFrame,
    entry_timestamp: Any,
) -> ReplayHigherTimeframeContext:
    """Build 4H/Daily trends without using the entry candle or any future data.

    Only lower-timeframe rows with timestamps strictly earlier than the entry
    timestamp are eligible. Therefore the current entry candle and all future
    candles are excluded from higher-timeframe construction.
    """
    timestamp = pd.Timestamp(entry_timestamp)
    eligible = history.loc[history.index < timestamp]

    trend_4h = normalize_trend(_trend_from_resampled(_completed_resample(eligible, "4h")))
    trend_1d = normalize_trend(_trend_from_resampled(_completed_resample(eligible, "1D")))

    directional = [trend for trend in (trend_4h, trend_1d) if trend in {"Bullish", "Bearish"}]

    if not directional:
        agreement = "NEUTRAL"
        aligned_direction = None
    elif len(set(directional)) > 1:
        agreement = "CONFLICTING"
        aligned_direction = None
    elif len(directional) == 2:
        agreement = "ALIGNED"
        aligned_direction = directional[0]
    else:
        agreement = "PARTIAL"
        aligned_direction = directional[0]

    return ReplayHigherTimeframeContext(
        trend_4h=trend_4h,
        trend_1d=trend_1d,
        agreement=agreement,
        aligned_direction=aligned_direction,
    )
