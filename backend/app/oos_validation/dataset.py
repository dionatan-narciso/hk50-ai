from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yfinance as yf

from app.oos_validation.contracts import ValidationPlan, ValidationWindow
from app.oos_validation.snapshot import load_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


DEFAULT_SYMBOL = "^HSI"
DEFAULT_INTERVAL = "1h"
DEFAULT_EMBARGO_DAYS = 7
DEFAULT_WARMUP_DAYS = 90


@dataclass(frozen=True)
class DiscoveryBounds:
    first_opened_at: datetime
    last_closed_at: datetime
    total_trades: int


def _as_utc_datetime(value: Any) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp.to_pydatetime()


def inspect_discovery_bounds(path: Path | None = None) -> DiscoveryBounds:
    """Read the frozen-discovery replay journal without modifying it."""
    journal_path = path or resolve_runtime_paths().replay_trade_journal
    if not journal_path.exists():
        raise FileNotFoundError(f"Replay discovery journal not found: {journal_path}")

    journal = pd.read_csv(journal_path)
    required = {"opened_at", "closed_at"}
    if not required.issubset(journal.columns):
        missing = ", ".join(sorted(required - set(journal.columns)))
        raise ValueError(f"Replay discovery journal is missing columns: {missing}")
    if journal.empty:
        raise ValueError("Replay discovery journal is empty")

    opened = pd.to_datetime(journal["opened_at"], utc=True, errors="coerce")
    closed = pd.to_datetime(journal["closed_at"], utc=True, errors="coerce")
    valid = opened.notna() & closed.notna()
    if not valid.all():
        raise ValueError("Replay discovery journal contains invalid trade timestamps")

    return DiscoveryBounds(
        first_opened_at=_as_utc_datetime(opened.min()),
        last_closed_at=_as_utc_datetime(closed.max()),
        total_trades=int(len(journal)),
    )


def candidate_snapshot_frozen_at(path: Path | None = None) -> datetime:
    """Use the local frozen snapshot creation time as the OOS data cutoff."""
    snapshot_path = path or resolve_runtime_paths().validation_candidate_snapshot
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Frozen candidate snapshot not found: {snapshot_path}")
    return datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=timezone.utc)


def build_default_validation_plan(
    *,
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    validation_end: datetime | None = None,
    discovery_path: Path | None = None,
) -> ValidationPlan:
    """Build a deterministic post-discovery OOS plan with a safety embargo."""
    if embargo_days < 0:
        raise ValueError("embargo_days must be non-negative")

    bounds = inspect_discovery_bounds(discovery_path)
    discovery_end = bounds.last_closed_at + timedelta(hours=1)
    validation_start = discovery_end + timedelta(days=embargo_days)
    end = validation_end or candidate_snapshot_frozen_at()
    end = _as_utc_datetime(end)

    # Exclude a potentially incomplete hourly candle at the freeze boundary.
    end = end.replace(minute=0, second=0, microsecond=0)
    if end <= validation_start:
        raise ValueError("No post-discovery OOS window exists before the candidate freeze cutoff")

    return ValidationPlan(
        symbol=symbol,
        interval=interval,
        discovery=ValidationWindow(
            start=bounds.first_opened_at,
            end=discovery_end,
        ),
        validation=ValidationWindow(
            start=validation_start,
            end=end,
        ),
    )


def _normalise_market_data(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]
    if not set(required).issubset(data.columns):
        missing = ", ".join(sorted(set(required) - set(data.columns)))
        raise ValueError(f"Downloaded OOS data is missing columns: {missing}")

    index = pd.to_datetime(data.index, utc=True, errors="coerce")
    valid = ~index.isna()
    data = data.loc[valid].copy()
    data.index = index[valid]
    data = data.sort_index()
    data = data[~data.index.duplicated(keep="first")]
    data = data.dropna(subset=required)
    return data


def fetch_validation_market_data(
    plan: ValidationPlan,
    *,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
    downloader: Callable[..., pd.DataFrame] = yf.download,
) -> tuple[pd.DataFrame, datetime]:
    """Download raw OOS candles plus warm-up history; score only the OOS window later."""
    if warmup_days < 1:
        raise ValueError("warmup_days must be at least 1")

    warmup_start = plan.validation.start - timedelta(days=warmup_days)
    frame = downloader(
        plan.symbol,
        start=warmup_start,
        end=plan.validation.end,
        interval=plan.interval,
        progress=False,
        auto_adjust=False,
    )
    data = _normalise_market_data(frame)
    if data.empty:
        raise ValueError("No OOS market data returned for the requested window")

    start_ts = pd.Timestamp(warmup_start)
    end_ts = pd.Timestamp(plan.validation.end)
    data = data.loc[(data.index >= start_ts) & (data.index < end_ts)].copy()
    if data.empty:
        raise ValueError("Downloaded OOS data contains no rows inside the requested fetch window")

    scored = data.loc[data.index >= pd.Timestamp(plan.validation.start)]
    if scored.empty:
        raise ValueError("Downloaded OOS data contains no candles in the scored validation window")

    return data, warmup_start


def _dataset_csv_bytes(data: pd.DataFrame) -> bytes:
    output = data.copy()
    output.index.name = "timestamp_utc"
    return output.to_csv(lineterminator="\n").encode("utf-8")


def _manifest_digest(body: dict[str, Any]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_validation_dataset(
    plan: ValidationPlan,
    data: pd.DataFrame,
    warmup_start: datetime,
) -> dict[str, Any]:
    """Freeze one immutable OOS market dataset tied to the frozen candidate snapshot."""
    snapshot = load_candidate_snapshot()
    paths = resolve_runtime_paths()
    csv_bytes = _dataset_csv_bytes(data)
    dataset_sha256 = hashlib.sha256(csv_bytes).hexdigest()

    scored_rows = int((data.index >= pd.Timestamp(plan.validation.start)).sum())
    body = {
        "schema_version": 1,
        "symbol": plan.symbol,
        "interval": plan.interval,
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "discovery_total_trades": snapshot["discovery_total_trades"],
        "discovery_window": {
            "start": plan.discovery.start.isoformat(),
            "end": plan.discovery.end.isoformat(),
        },
        "validation_window": {
            "start": plan.validation.start.isoformat(),
            "end": plan.validation.end.isoformat(),
        },
        "warmup_start": warmup_start.isoformat(),
        "row_count": int(len(data)),
        "scored_row_count": scored_rows,
        "dataset_sha256": dataset_sha256,
    }
    manifest = {**body, "manifest_sha256": _manifest_digest(body)}

    paths.validation_dir.mkdir(parents=True, exist_ok=True)
    if paths.validation_dataset_manifest.exists() or paths.validation_market_data.exists():
        if not (paths.validation_dataset_manifest.exists() and paths.validation_market_data.exists()):
            raise RuntimeError("OOS dataset freeze is incomplete; both dataset and manifest are required")

        existing_manifest = json.loads(
            paths.validation_dataset_manifest.read_text(encoding="utf-8")
        )
        existing_body = {
            key: value for key, value in existing_manifest.items() if key != "manifest_sha256"
        }
        if existing_manifest.get("manifest_sha256") != _manifest_digest(existing_body):
            raise ValueError("Frozen OOS dataset manifest integrity check failed")

        existing_bytes = paths.validation_market_data.read_bytes()
        existing_dataset_sha = hashlib.sha256(existing_bytes).hexdigest()
        if existing_dataset_sha != existing_manifest.get("dataset_sha256"):
            raise ValueError("Frozen OOS market dataset integrity check failed")

        if existing_manifest != manifest or existing_bytes != csv_bytes:
            raise RuntimeError("OOS market dataset is already frozen with different content")
        return existing_manifest

    paths.validation_market_data.write_bytes(csv_bytes)
    paths.validation_dataset_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def build_and_freeze_default_oos_dataset(
    *,
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    embargo_days: int = DEFAULT_EMBARGO_DAYS,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
    validation_end: datetime | None = None,
    downloader: Callable[..., pd.DataFrame] = yf.download,
) -> dict[str, Any]:
    plan = build_default_validation_plan(
        symbol=symbol,
        interval=interval,
        embargo_days=embargo_days,
        validation_end=validation_end,
    )
    data, warmup_start = fetch_validation_market_data(
        plan,
        warmup_days=warmup_days,
        downloader=downloader,
    )
    return freeze_validation_dataset(plan, data, warmup_start)
