from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yfinance as yf

from app.oos_validation.dataset import _normalise_market_data
from app.oos_validation.forward_batches import get_forward_batch_dir
from app.oos_validation.snapshot import load_candidate_snapshot


DEFAULT_BATCH_DAYS = 14
DEFAULT_WARMUP_DAYS = 90
DEFAULT_SYMBOL = "^HSI"
DEFAULT_INTERVAL = "1h"


def _registry() -> dict[str, Any]:
    path = get_forward_batch_dir() / "registry.json"
    if not path.exists():
        raise FileNotFoundError("Forward OOS registry is missing. Register Batch 1 first.")
    return json.loads(path.read_text(encoding="utf-8"))


def next_batch_id(registry: dict[str, Any] | None = None) -> str:
    batches = (registry or _registry()).get("batches", [])
    return f"batch-{len(batches) + 1:03d}"


def _utc(value: Any) -> datetime:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    else:
        stamp = stamp.tz_convert("UTC")
    return stamp.to_pydatetime()


def inspect_next_batch(
    *,
    now: datetime | None = None,
    batch_days: int = DEFAULT_BATCH_DAYS,
) -> dict[str, Any]:
    if batch_days < 1:
        raise ValueError("batch_days must be at least 1")
    registry = _registry()
    batches = registry.get("batches", [])
    if not batches:
        raise ValueError("Forward OOS registry has no Batch 1")

    previous = batches[-1]
    start = _utc(previous["validation_window"]["end"])
    end = start + timedelta(days=batch_days)
    current = _utc(now or datetime.now(timezone.utc)).replace(
        minute=0, second=0, microsecond=0
    )
    ready = current >= end
    return {
        "status": "ready" if ready else "not_ready",
        "batch_id": next_batch_id(registry),
        "previous_batch_id": previous["batch_id"],
        "candidate_snapshot_sha256": previous["candidate_snapshot_sha256"],
        "validation_window": {"start": start.isoformat(), "end": end.isoformat()},
        "ready_at": end.isoformat(),
        "current_cutoff": current.isoformat(),
        "batch_days": batch_days,
        "note": (
            "Batch may be frozen now."
            if ready
            else "No new batch is created until the full forward window has elapsed."
        ),
    }


def _batch_paths(batch_id: str) -> dict[str, Path]:
    folder = get_forward_batch_dir() / batch_id
    return {
        "folder": folder,
        "dataset": folder / "market_data.csv",
        "manifest": folder / "dataset_manifest.json",
        "journal": folder / "trade_journal.csv",
        "report": folder / "result_report.json",
    }


def get_batch_paths(batch_id: str) -> dict[str, Path]:
    return _batch_paths(batch_id)


def _csv_bytes(data: pd.DataFrame) -> bytes:
    output = data.copy()
    output.index.name = "timestamp_utc"
    return output.to_csv(lineterminator="\n").encode("utf-8")


def _manifest_sha(body: dict[str, Any]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_next_batch_dataset(
    *,
    now: datetime | None = None,
    batch_days: int = DEFAULT_BATCH_DAYS,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    downloader: Callable[..., pd.DataFrame] = yf.download,
) -> dict[str, Any]:
    plan = inspect_next_batch(now=now, batch_days=batch_days)
    if plan["status"] != "ready":
        raise RuntimeError(
            f"{plan['batch_id']} is not ready until {plan['ready_at']}"
        )
    if warmup_days < 1:
        raise ValueError("warmup_days must be at least 1")

    registry = _registry()
    first = registry["batches"][0]
    execution_start = _utc(first["validation_window"]["start"])
    validation_start = _utc(plan["validation_window"]["start"])
    validation_end = _utc(plan["validation_window"]["end"])
    fetch_start = execution_start - timedelta(days=warmup_days)

    frame = downloader(
        symbol,
        start=fetch_start,
        end=validation_end,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    data = _normalise_market_data(frame)
    if data.empty:
        raise ValueError("No forward OOS market data returned")
    data = data.loc[
        (data.index >= pd.Timestamp(fetch_start))
        & (data.index < pd.Timestamp(validation_end))
    ].copy()
    scored = data.loc[
        (data.index >= pd.Timestamp(validation_start))
        & (data.index < pd.Timestamp(validation_end))
    ]
    if scored.empty:
        raise ValueError("Forward OOS dataset contains no scored candles")

    snapshot = load_candidate_snapshot()
    if snapshot["snapshot_sha256"] != plan["candidate_snapshot_sha256"]:
        raise RuntimeError("Frozen candidate snapshot does not match forward registry")

    paths = _batch_paths(plan["batch_id"])
    csv_bytes = _csv_bytes(data)
    dataset_sha = hashlib.sha256(csv_bytes).hexdigest()
    body = {
        "schema_version": 1,
        "batch_id": plan["batch_id"],
        "symbol": symbol,
        "interval": interval,
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "execution_start": execution_start.isoformat(),
        "validation_window": plan["validation_window"],
        "warmup_start": fetch_start.isoformat(),
        "row_count": int(len(data)),
        "scored_row_count": int(len(scored)),
        "dataset_sha256": dataset_sha,
    }
    manifest = {**body, "manifest_sha256": _manifest_sha(body)}

    if paths["dataset"].exists() or paths["manifest"].exists():
        if not (paths["dataset"].exists() and paths["manifest"].exists()):
            raise RuntimeError("Forward OOS batch freeze is incomplete")
        existing = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        existing_bytes = paths["dataset"].read_bytes()
        if existing != manifest or existing_bytes != csv_bytes:
            raise RuntimeError("Forward OOS batch is already frozen with different content")
        return existing

    paths["folder"].mkdir(parents=True, exist_ok=True)
    paths["dataset"].write_bytes(csv_bytes)
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest
