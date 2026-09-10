# Sprint 1C — Out-of-Sample Context Validation

## Purpose

Sprint 1C validates Sprint 1B context hypotheses on historical data that was not used to discover or rank those hypotheses.

## Core anti-overfitting rules

1. Discovery and validation windows must not overlap.
2. Candidate hypotheses must be frozen before OOS results are inspected.
3. A frozen candidate snapshot is content-hashed and cannot be replaced by a different snapshot through the normal freeze path.
4. OOS trades are stored under `data/validation`, never `data/replay` or `data/paper`.
5. Discovery metrics are reference metadata only; OOS classification must be based on validation results.
6. OOS validation is research-only until a later sprint explicitly approves context influence on trading decisions.

## Runtime isolation

- Discovery replay journal: `data/replay/replay_trade_journal.csv`
- OOS validation journal: `data/validation/validation_trade_journal.csv`
- Frozen hypotheses: `data/validation/frozen_context_candidates.json`
- Validation result report: `data/validation/validation_result_report.json`

## Candidate freeze

`python scripts/freeze_oos_candidates.py` builds the final Sprint 1B candidate report, retains PROMISING and WATCH hypotheses, assigns deterministic IDs, and writes one integrity-checked snapshot.

Re-running the command with identical discovery content is safe. If the candidate set changes after the snapshot has been frozen, the command fails instead of silently replacing the hypotheses.

## Dataset plan

`ValidationPlan` owns a discovery window and a validation window. Both timestamps must be timezone-aware, discovery must precede validation, and overlap is rejected.

Sprint 1C.1 defines this architecture only. A later Sprint 1C stage will source and run the actual unseen historical period.

## Trading impact

None. Sprint 1C.1 does not modify strategy rules, signal generation, voting, confidence, risk, exits, position sizing, or learning.
