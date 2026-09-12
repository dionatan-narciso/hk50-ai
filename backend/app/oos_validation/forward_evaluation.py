from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.oos_validation.evaluation import _classification, _matches_context, _metrics
from app.oos_validation.evidence import classify_evidence
from app.oos_validation.forward_batches import (
    build_batch_manifest,
    get_forward_batch_dir,
    register_batch,
)
from app.oos_validation.forward_dataset import get_batch_paths
from app.oos_validation.forward_engine import run_forward_batch_replay
from app.oos_validation.snapshot import load_candidate_snapshot
from app.runtime_paths import resolve_runtime_paths


def _read_journal(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _cumulative_journal(current_batch_id: str) -> pd.DataFrame:
    root = get_forward_batch_dir()
    registry_path = root / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    frames: list[pd.DataFrame] = []

    batch1 = resolve_runtime_paths().validation_trade_journal
    if batch1.exists():
        frames.append(pd.read_csv(batch1))

    for item in registry.get("batches", []):
        batch_id = item["batch_id"]
        if batch_id == "batch-001" or batch_id == current_batch_id:
            continue
        path = get_batch_paths(batch_id)["journal"]
        if path.exists():
            frames.append(pd.read_csv(path))

    current_path = get_batch_paths(current_batch_id)["journal"]
    if current_path.exists():
        frames.append(pd.read_csv(current_path))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def _candidate_results(journal: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    snapshot = load_candidate_snapshot()
    baseline = _metrics(journal)
    baseline_average = float(baseline["average_return"])
    results = []

    for candidate in snapshot.get("candidates", []):
        context = candidate["context"]
        metrics = _metrics(_matches_context(journal, context))
        validation_average = float(metrics["average_return"])
        raw_delta = round(validation_average - baseline_average, 3)
        directional_lift = (
            raw_delta
            if candidate["direction"] == "POSITIVE"
            else round(baseline_average - validation_average, 3)
        )
        discovery_average = float(candidate["discovery_average_return"])
        same_sign = (
            validation_average > 0
            if candidate["direction"] == "POSITIVE"
            else validation_average < 0
        )
        retention = None
        if discovery_average != 0 and same_sign:
            retention = round(abs(validation_average / discovery_average), 3)

        evidence = classify_evidence(int(metrics["trades"]))
        results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "classification": candidate["classification"],
                "direction": candidate["direction"],
                "context": context,
                "discovery_average_return": discovery_average,
                "validation": metrics,
                "effect_retention_ratio": retention,
                "directional_lift_vs_baseline": directional_lift,
                "evidence_level": evidence.label,
                "evidence_description": evidence.description,
                "oos_status": _classification(
                    direction=candidate["direction"],
                    validation_metrics=metrics,
                    directional_lift=directional_lift,
                ),
            }
        )
    return baseline, results


def evaluate_and_register_forward_batch(batch_id: str) -> dict[str, Any]:
    replay_summary = run_forward_batch_replay(batch_id)
    paths = get_batch_paths(batch_id)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    snapshot = load_candidate_snapshot()
    if manifest["candidate_snapshot_sha256"] != snapshot["snapshot_sha256"]:
        raise RuntimeError("Forward batch candidate snapshot does not match frozen hypotheses")

    batch_journal = _read_journal(paths["journal"])
    batch_baseline, batch_candidates = _candidate_results(batch_journal)
    cumulative = _cumulative_journal(batch_id)
    cumulative_baseline, cumulative_candidates = _candidate_results(cumulative)

    registration = build_batch_manifest(
        batch_id=batch_id,
        candidate_snapshot_sha256=manifest["candidate_snapshot_sha256"],
        dataset_sha256=manifest["dataset_sha256"],
        validation_start=pd.Timestamp(manifest["validation_window"]["start"]).to_pydatetime(),
        validation_end=pd.Timestamp(manifest["validation_window"]["end"]).to_pydatetime(),
        scored_row_count=manifest["scored_row_count"],
        trade_count=replay_summary["total_trades"],
    )
    registry = register_batch(registration)

    status_counts = {
        label: sum(1 for item in cumulative_candidates if item["oos_status"] == label)
        for label in ("PASS", "FAIL", "INCONCLUSIVE")
    }
    evidence_counts: dict[str, int] = {}
    for item in cumulative_candidates:
        label = item["evidence_level"]
        evidence_counts[label] = evidence_counts.get(label, 0) + 1

    report = {
        "status": "completed",
        "mode": "forward_oos_batch_evaluation",
        "batch_id": batch_id,
        "candidate_snapshot_sha256": snapshot["snapshot_sha256"],
        "batch": {
            "baseline": batch_baseline,
            "candidates": batch_candidates,
            "replay_summary": replay_summary,
        },
        "cumulative": {
            "baseline": cumulative_baseline,
            "status_counts": status_counts,
            "evidence_counts": evidence_counts,
            "candidates": cumulative_candidates,
        },
        "registered_batch_count": len(registry["batches"]),
        "note": (
            "Cumulative evidence includes Batch 1 plus all registered forward batches. "
            "Candidate definitions remain frozen and no production trading logic is changed."
        ),
    }
    paths["report"].write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return report
