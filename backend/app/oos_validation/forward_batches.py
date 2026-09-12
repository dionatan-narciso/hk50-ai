from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from app.runtime_paths import resolve_runtime_paths


REGISTRY_SCHEMA_VERSION = 1


def get_forward_batch_dir() -> Path:
    path = resolve_runtime_paths().validation_dir / "forward_batches"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_forward_batch_registry_path() -> Path:
    return get_forward_batch_dir() / "registry.json"


def _digest(body: dict[str, Any]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_registry() -> dict[str, Any]:
    path = get_forward_batch_registry_path()
    if not path.exists():
        return {"schema_version": REGISTRY_SCHEMA_VERSION, "batches": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported forward OOS registry schema")
    return registry


def register_batch(manifest: dict[str, Any]) -> dict[str, Any]:
    """Register an immutable validation batch and reject overlap or mutation."""
    required = {
        "batch_id",
        "candidate_snapshot_sha256",
        "dataset_sha256",
        "validation_window",
        "scored_row_count",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"Forward batch manifest missing fields: {', '.join(sorted(missing))}")

    start = datetime.fromisoformat(manifest["validation_window"]["start"])
    end = datetime.fromisoformat(manifest["validation_window"]["end"])
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("Forward batch validation window must be timezone-aware and ordered")

    registry = _load_registry()
    batches = registry["batches"]
    for existing in batches:
        if existing["batch_id"] == manifest["batch_id"]:
            if existing != manifest:
                raise RuntimeError("Forward OOS batch ID is already frozen with different content")
            return registry
        existing_start = datetime.fromisoformat(existing["validation_window"]["start"])
        existing_end = datetime.fromisoformat(existing["validation_window"]["end"])
        if start < existing_end and existing_start < end:
            raise RuntimeError("Forward OOS validation batches may not overlap")

    batches.append(dict(manifest))
    batches.sort(key=lambda item: item["validation_window"]["start"])
    body = {"schema_version": REGISTRY_SCHEMA_VERSION, "batches": batches}
    body["registry_sha256"] = _digest(body)
    get_forward_batch_registry_path().write_text(
        json.dumps(body, indent=2, sort_keys=True), encoding="utf-8"
    )
    return body


def build_batch_manifest(
    *,
    batch_id: str,
    candidate_snapshot_sha256: str,
    dataset_sha256: str,
    validation_start: datetime,
    validation_end: datetime,
    scored_row_count: int,
    trade_count: int | None = None,
) -> dict[str, Any]:
    if validation_start.tzinfo is None or validation_end.tzinfo is None:
        raise ValueError("Forward batch timestamps must be timezone-aware")
    return {
        "batch_id": batch_id,
        "candidate_snapshot_sha256": candidate_snapshot_sha256,
        "dataset_sha256": dataset_sha256,
        "validation_window": {
            "start": validation_start.astimezone(timezone.utc).isoformat(),
            "end": validation_end.astimezone(timezone.utc).isoformat(),
        },
        "scored_row_count": int(scored_row_count),
        "trade_count": None if trade_count is None else int(trade_count),
    }
