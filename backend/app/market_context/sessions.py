from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone


@dataclass(frozen=True)
class TradingSessionContext:
    """Informational trading-session classification for one UTC timestamp."""

    timestamp_utc: datetime
    active_sessions: tuple[str, ...]
    label: str
    is_overlap: bool
    is_quiet: bool


def _in_window(value: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def derive_trading_session_context(timestamp: datetime) -> TradingSessionContext:
    """Classify a timezone-aware timestamp into broad global trading sessions.

    Session windows are fixed in UTC so live and replay classification is
    deterministic. These labels are informational only in Sprint 1B.4 and do
    not alter strategy, voting, confidence, or risk behavior.
    """
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Trading session timestamp must be timezone-aware.")

    timestamp_utc = timestamp.astimezone(timezone.utc)
    clock = timestamp_utc.time().replace(tzinfo=None)

    sessions: list[str] = []
    windows = (
        ("ASIA", time(0, 0), time(9, 0)),
        ("EUROPE", time(7, 0), time(16, 0)),
        ("US", time(13, 0), time(22, 0)),
    )

    for name, start, end in windows:
        if _in_window(clock, start, end):
            sessions.append(name)

    active_sessions = tuple(sessions)
    is_overlap = len(active_sessions) > 1
    is_quiet = not active_sessions

    if is_quiet:
        label = "QUIET"
    elif is_overlap:
        label = "+".join(active_sessions)
    else:
        label = active_sessions[0]

    return TradingSessionContext(
        timestamp_utc=timestamp_utc,
        active_sessions=active_sessions,
        label=label,
        is_overlap=is_overlap,
        is_quiet=is_quiet,
    )
