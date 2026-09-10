from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class ValidationWindow:
    """Closed-open historical window used by discovery or OOS validation."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("ValidationWindow timestamps must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("ValidationWindow start must be before end")

    def overlaps(self, other: "ValidationWindow") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class ValidationPlan:
    """Immutable dataset-separation contract for one OOS experiment."""

    symbol: str
    interval: str
    discovery: ValidationWindow
    validation: ValidationWindow

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("ValidationPlan symbol must not be empty")
        if not self.interval.strip():
            raise ValueError("ValidationPlan interval must not be empty")
        if self.discovery.overlaps(self.validation):
            raise ValueError("Discovery and validation windows must not overlap")
        if self.discovery.end > self.validation.start:
            raise ValueError("Validation window must begin after discovery window ends")


@dataclass(frozen=True)
class CandidateHypothesis:
    """Frozen context hypothesis carried from discovery into OOS validation."""

    candidate_id: str
    direction: str
    classification: str
    context: Mapping[str, str]
    discovery_trades: int
    discovery_average_return: float
    discovery_profit_factor: float | None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be empty")
        if self.direction not in {"POSITIVE", "NEGATIVE"}:
            raise ValueError("direction must be POSITIVE or NEGATIVE")
        if not self.context:
            raise ValueError("context must not be empty")
        if self.discovery_trades < 1:
            raise ValueError("discovery_trades must be at least 1")
