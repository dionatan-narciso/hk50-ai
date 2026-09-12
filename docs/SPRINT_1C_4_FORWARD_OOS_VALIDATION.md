# Sprint 1C.4 — Forward OOS Validation

## Purpose

Sprint 1C.3 produced four completed unseen trades. All 26 frozen context hypotheses therefore remain inconclusive. Sprint 1C.4 preserves that evidence and establishes an append-only sequence of non-overlapping forward-validation batches.

## Rules

- The Sprint 1B candidate snapshot remains frozen.
- Batch 1 is never replaced or extended in place.
- Later batches begin at or after the prior batch end and may not overlap.
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

After pulling this sprint and passing tests, register the already-completed first OOS run with:

```bash
python scripts/register_oos_batch_1.py
```

This command does not download new market data and does not rerun trading. It records the existing frozen dataset/result as Batch 1.

## Next implementation stage

Sprint 1C.4.2 will add acquisition and evaluation of Batch 2+ using only candles after the previous registered batch end, while retaining sufficient pre-window warm-up for indicators. Each batch will be frozen independently before evaluation.
