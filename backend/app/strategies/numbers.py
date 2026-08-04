from __future__ import annotations

from typing import Any


def clean_number(value: Any, default: float = 0) -> float:
    """Preserve the existing strategy numeric-conversion behavior."""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace(",", ""))
    except Exception:
        return default
