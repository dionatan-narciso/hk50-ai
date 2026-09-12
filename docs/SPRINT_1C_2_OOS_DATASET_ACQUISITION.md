# Sprint 1C.2 — Unseen Historical Dataset Acquisition

## Purpose

Sprint 1C.2 creates a reproducible, immutable market dataset for out-of-sample validation of the frozen Sprint 1B context hypotheses.

No strategy rules, thresholds, weights, voting logic, entries, exits, replay learning logic, paper state, or live state are changed by this sprint.

## Anti-overfitting boundaries

The candidate snapshot from Sprint 1C.1 remains the hypothesis source. The OOS dataset is tied to that snapshot by SHA-256 and is frozen separately in the validation runtime namespace.

The default validation plan:

- reads the original discovery trade boundaries from `replay/replay_trade_journal.csv`;
- treats one hour after the final discovery close as the closed-open discovery boundary;
- adds a seven-day embargo before scored OOS candles begin;
- ends at the local candidate snapshot freeze time, rounded down to the previous whole UTC hour;
- downloads 90 days of warm-up history before the scored OOS start so higher-timeframe indicators can initialize;
- never scores warm-up candles as OOS evidence.

The validation window must occur strictly after the discovery window. Existing `ValidationPlan` overlap guards remain active.

## Runtime files

Sprint 1C.2 adds two validation-only files:

- `data/validation/validation_market_data.csv`
- `data/validation/validation_dataset_manifest.json`

The manifest records:

- discovery and validation windows;
- warm-up start;
- symbol and interval;
- frozen candidate snapshot hash;
- market dataset hash;
- manifest hash;
- total market-data rows;
- scored OOS rows.

Once created, a different dataset cannot replace the frozen dataset through the normal build path. Manual changes to either the manifest or market-data file are detected by integrity checks.

## Commands

Inspect boundaries without downloading or changing validation data:

```bash
python scripts/inspect_oos_dataset_plan.py
```

Build and freeze the OOS dataset:

```bash
python scripts/build_oos_dataset.py
```

The build uses `^HSI`, `1h`, seven embargo days, and 90 warm-up days by default to preserve the current HK50 replay research scope.

## What this sprint does not do

Sprint 1C.2 does not run the frozen hypotheses against the OOS dataset and does not produce pass/fail candidate results. That belongs to the next validation stage after the dataset and its integrity fingerprint have been confirmed.
