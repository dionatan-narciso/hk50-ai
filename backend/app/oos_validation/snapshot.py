from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.runtime_paths import resolve_runtime_paths


ELIGIBLE_CLASSIFICATIONS = {"PROMISING", "WATCH"}


def _candidate_id(candidate: dict[str, Any]) -> str:
    payload = {
        "direction": candidate["direction"],
        "context": candidate["representative"]["context"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def build_candidate_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic immutable-style snapshot from Sprint 1B candidates."""
    if report.get("status") != "completed":
        raise ValueError("candidate report must be completed before freezing")

    candidates = []
    for candidate in report.get("candidates", []):
        if candidate.get("classification") not in ELIGIBLE_CLASSIFICATIONS:
            continue
        representative = candidate.get("representative", {})
        context = representative.get("context", {})
        if not context:
            continue
        candidates.append(
            {
                "candidate_id": _candidate_id(candidate),
                "classification": candidate["classification"],
                "direction": candidate["direction"],
                "context": dict(sorted(context.items())),
                "discovery_trades": int(candidate["trades"]),
                "discovery_win_rate": float(candidate["win_rate"]),
                "discovery_average_return": float(candidate["average_return"]),
                "discovery_profit_factor": candidate.get("profit_factor"),
                "discovery_fold_consistency_percent": float(
                    candidate.get("fold_consistency_percent", 0)
                ),
            }
        )

    candidates.sort(key=lambda item: item["candidate_id"])
    body = {
        "schema_version": 1,
        "discovery_total_trades": int(report.get("total_trades", 0)),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**body, "snapshot_sha256": digest}


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    supplied = snapshot.get("snapshot_sha256")
    body = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    expected = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if supplied != expected:
        raise ValueError("Frozen candidate snapshot integrity check failed")


def freeze_candidate_snapshot(report: dict[str, Any]) -> Path:
    """Freeze hypotheses once; refuse later content changes during OOS validation."""
    snapshot = build_candidate_snapshot(report)
    path = resolve_runtime_paths().validation_candidate_snapshot
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        _validate_snapshot(existing)
        if existing.get("snapshot_sha256") != snapshot.get("snapshot_sha256"):
            raise RuntimeError(
                "OOS candidate snapshot is already frozen with different content"
            )
        return path

    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_candidate_snapshot() -> dict[str, Any]:
    path = resolve_runtime_paths().validation_candidate_snapshot
    if not path.exists():
        raise FileNotFoundError(f"Frozen candidate snapshot not found: {path}")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    _validate_snapshot(snapshot)
    return snapshot
