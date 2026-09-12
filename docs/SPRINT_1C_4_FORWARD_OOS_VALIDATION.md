# Sprint 1C.4 — Forward OOS Validation

## Purpose

Sprint 1C.3 produced four completed unseen trades. All 26 frozen context hypotheses therefore remain inconclusive. Sprint 1C.4 preserves that evidence and establishes an append-only sequence of non-overlapping forward-validation batches.

## Rules

- The Sprint 1B candidate snapshot remains frozen.
- Batch 1 is never replaced or extended in place.
- Later batches may not overlap.
- Each batch records the candidate snapshot SHA256 and dataset SHA256.
- Forward validation must not update replay, paper, or live learning state.
- Insufficient evidence is not converted into a pass/fail by lowering thresholds.
- No candidate is promoted into production trading logic during Sprint 1C.4.

## Evidence ladder

| Completed matching OOS trades | Evidence level |
| ---: | --- |
| 0–4 | INSUFFICIENT |
| 5–9 | PRELIMINARY |
| 10–19 | DEVELOPING |
| 20–29 | MEANINGFUL |
| 30+ | STRONGER_EVIDENCE |

The ladder describes sample maturity, not profitability. A candidate can accumulate stronger evidence and still fail validation.

## Batch registry

Forward batches are registered under `data/validation/forward_batches/registry.json`. Registration is idempotent for identical content and rejects mutation or overlapping windows.

## Batch 1

The first completed OOS run is registered with:

```bash
python scripts/register_oos_batch_1.py
```

Batch 1 covers 2026-08-24 08:30 UTC through 2026-09-12 11:00 UTC and contains four completed trades.

## Sprint 1C.4.2 — Incremental batches

Later batches use fixed 14-day validation windows. This prevents repeated tiny samples from being frozen simply because validation was checked frequently.

Inspect the next window with:

```bash
python scripts/inspect_next_oos_batch.py
```

For the currently registered Batch 1, Batch 2 is:

- start: 2026-09-12 11:00 UTC
- end / ready-at: 2026-09-26 11:00 UTC

The builder refuses to create Batch 2 before the full window has elapsed.

Once a batch is ready, freeze its market dataset with:

```bash
python scripts/build_next_oos_batch.py
```

Each batch is stored independently under `data/validation/forward_batches/<batch-id>/` with its own market dataset, manifest, trade journal and result report.

## Position continuity

Forward batches must not reset the trading path at their boundary. Batch 1 ended with an open position, so later replay reconstructs the trading state from the original OOS execution start while journaling and scoring only trades that close inside the current batch. This permits a trade opened before a batch boundary to close naturally in a later batch without editing earlier evidence.

## Evaluation

After the batch dataset is frozen, run:

```bash
python scripts/run_next_oos_batch.py
```

The forward evaluator:

- reconstructs continuous OOS trading state;
- scores only the new batch;
- keeps the frozen candidate snapshot unchanged;
- registers the completed batch only after evaluation;
- combines Batch 1 and later journals into cumulative candidate evidence;
- reports PASS / FAIL / INCONCLUSIVE separately from the evidence-maturity ladder.

No production trading behaviour is changed by this process.
