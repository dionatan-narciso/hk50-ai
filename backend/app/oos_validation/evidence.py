from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceLevel:
    label: str
    minimum_trades: int
    description: str


EVIDENCE_LEVELS = (
    EvidenceLevel("INSUFFICIENT", 0, "Too little unseen evidence for a directional judgement."),
    EvidenceLevel("PRELIMINARY", 5, "Early unseen evidence only; never sufficient for production promotion."),
    EvidenceLevel("DEVELOPING", 10, "Developing unseen evidence; continue forward validation."),
    EvidenceLevel("MEANINGFUL", 20, "Meaningful unseen sample, still subject to robustness and risk review."),
    EvidenceLevel("STRONGER_EVIDENCE", 30, "Stronger unseen evidence suitable for later integration review."),
)


def classify_evidence(trades: int) -> EvidenceLevel:
    if trades < 0:
        raise ValueError("trades must be non-negative")
    selected = EVIDENCE_LEVELS[0]
    for level in EVIDENCE_LEVELS:
        if trades >= level.minimum_trades:
            selected = level
    return selected
