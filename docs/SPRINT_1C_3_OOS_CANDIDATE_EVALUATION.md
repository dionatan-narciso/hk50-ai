# Sprint 1C.3 — OOS Candidate Evaluation

## Purpose

Evaluate the 26 frozen Sprint 1B context hypotheses against the frozen post-discovery HK50 validation dataset without retuning hypotheses or changing trading behaviour.

## Isolation rules

- Candidate definitions come only from `data/validation/frozen_context_candidates.json`.
- Market candles come only from the frozen validation dataset and its integrity-checked manifest.
- Validation trades are written only to `data/validation/validation_trade_journal.csv`.
- Results are written only to `data/validation/validation_result_report.json`.
- Replay, paper and live journals/memories are not updated by OOS validation.
- Replay learning memory/control are read-only discovery inputs. Their SHA-256 fingerprints and the replay entry weights used are recorded in the validation replay summary.
- Warm-up candles initialise indicators and higher-timeframe context but cannot open scored trades.

## Trading behaviour

The validation replay reuses the historical replay helpers for market snapshots, strategy decisions, adaptive exits, replay penalties and entry-context scoring. Entry-context scoring explicitly uses replay/discovery weights rather than paper weights.

The validation engine deliberately does not call replay learning updates or the replay learning controller writer after the run.

## Candidate evaluation

Each frozen candidate is matched against completed validation trades using its exact frozen context values.

Reported metrics include:

- OOS trade count
- wins/losses and win rate
- average, median and total return
- profit factor
- discovery versus validation effect size
- effect-retention ratio when the sign persists
- raw average-return delta versus the OOS baseline
- directional lift versus the OOS baseline

## PASS / FAIL / INCONCLUSIVE

A candidate is `INCONCLUSIVE` until it has at least 5 matching OOS trades.

With at least 5 trades, `PASS` requires:

- average return remains in the frozen candidate's expected direction;
- profit factor, when defined, is on the expected side of 1; and
- the candidate improves in its expected direction versus the complete OOS trade baseline.

Otherwise it is `FAIL`.

These labels are research conclusions only. They do not change production strategy rules, voting, confidence, entries, exits or position sizing.

## Command

After the OOS dataset has been frozen:

```bash
python scripts/run_oos_validation.py
```

The console prints the compact baseline/status summary. The full per-candidate report is saved under the validation runtime namespace.
