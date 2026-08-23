# Sprint 1B — Market Context Evolution Closure

## Goal

Expand the trading platform from flat primary-timeframe indicators into a structured, replay-researchable market context while preserving production trading behaviour.

## Delivered

- Backward-compatible `MarketContext` enrichment namespaces.
- Multi-timeframe snapshot model.
- Higher-timeframe trend summaries.
- Timezone-safe session context.
- Volatility and trend-strength descriptors.
- Objective market-structure descriptors.
- Unified enrichment pipeline.
- Replay context instrumentation.
- Leak-free post-replay 4H/Daily enrichment using only candles strictly before entry time.
- Context outcome analysis.
- Context combination matrix with minimum sample controls.
- Chronological fold robustness analysis.
- Exact-trade-membership candidate deduplication and evidence classification.

## Production behaviour

UNCHANGED throughout Sprint 1B.

The new context fields do not alter strategy signals, voting, confidence, position sizing, risk management, regime blocking, replay entry gating, exits, or learning weights.

## Current research baseline

The first enriched HK50 replay contained 84 completed trades. Context findings are hypotheses, not production rules.

Examples observed during Sprint 1B include strong-trend contexts with positive expectancy and price-between-moving-averages contexts with negative expectancy. These observations require broader out-of-sample validation before any use in live decisions.

## Research safeguards

- Higher-timeframe replay context excludes the entry candle and all future candles.
- Context analysis prioritizes expectancy rather than win rate alone.
- Combination analysis applies minimum trade-count thresholds.
- Robustness analysis checks expectancy sign across chronological folds.
- Candidate deduplication collapses patterns that match the exact same replay trades.

## Candidate classifications

`PROMISING` — robust across folds, sufficient sample, and material expectancy.

`WATCH` — robust but sample/effect strength remains too limited for promotion.

`INSUFFICIENT_SAMPLE` — robust sign but below the minimum research sample.

`REJECT` — expectancy is not chronologically consistent.

These labels are research-only.

## Known limitations

- The initial research sample is only 84 HK50 trades.
- Session and volatility diversity is limited for this sample.
- Context variables can be correlated; deduplication reduces exact duplicate evidence but does not prove statistical independence.
- No context candidate has passed external/out-of-sample validation yet.

## Closure status

Sprint 1B: COMPLETE pending local test-suite validation and candidate-report execution.

Ready next: out-of-sample context validation before any context feature is allowed to influence production trading behaviour.
