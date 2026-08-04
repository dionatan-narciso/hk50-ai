# Sprint 1A — Strategy Plugin Architecture

## Status

Sprint 1A establishes the strategy plugin foundation for the HK50 AI platform.
The migration preserves existing strategy thresholds, signals, reason wording,
vote rules, regime blocking, aliases, and response contracts.

## Core flow

```text
market data mapping
        |
        v
MarketContext
        |
        v
Strategy plugin
        |
        v
StrategyDecision
        |
        +--> registry-driven voting
        |
        +--> selected-strategy execution
```

## Contracts

### MarketContext

`app/strategies/contracts.py`

Provides the market-independent input contract:

- `symbol`
- `timeframe`
- `data`
- `metadata`
- dictionary-compatible `get()` access

The current production context remains `HK50` on `1h`.

### StrategyDecision

Standardizes plugin output:

- strategy name
- `BUY`, `SELL`, or `HOLD`
- reason
- optional confidence
- optional stop loss
- optional take profit
- metadata

### Strategy protocol

Every plugin exposes:

- `name`
- `metadata`
- `evaluate(context)`

## Plugin implementations

```text
app/strategies/rsi_pullback.py
app/strategies/ma_alignment.py
app/strategies/breakout.py
app/strategies/trend_following.py
app/strategies/rsi_30.py
```

Each module owns its strategy rules. `strategy_executor.py` no longer owns
strategy thresholds.

## Metadata and capabilities

`app/strategies/metadata.py`

Every plugin declares:

- version
- supported markets
- supported timeframes
- voting eligibility

Current declarations are intentionally conservative:

- market: `HK50`
- timeframe: `1h`
- version: `1.0.0`

The four established voting strategies are voting eligible. `RSI < 30` is
execution-only and remains excluded from voting.

## Registries

`app/strategies/default_registry.py`

Two explicit registries prevent accidental behavior changes.

### Voting registry

Ordered exactly as before:

1. RSI Pullback
2. MA Alignment
3. Breakout
4. Trend Following

All entries must support `HK50/1h` and declare voting eligibility.

### Execution registry

Contains the four voting strategies plus:

5. RSI < 30

Execution-only strategies do not need voting eligibility.

## Construction validation

`app/strategies/validation.py`

Registry construction fails early when:

- a plugin does not support the configured market
- a plugin does not support the configured timeframe
- a voting registry contains an execution-only plugin

Validation is construction-time only. It does not change runtime signal logic or
silently filter strategy results.

## Name resolution and regime blocking

`app/strategies/resolution.py`

Owns:

- extraction of research strategy names
- legacy alias mapping
- unknown-strategy fallback to Trend Following
- regime-block alias matching

This keeps name dispatch outside `strategy_executor.py`.

## Voting

`app/strategies/voting.py`

Production `run_strategy_vote()` delegates to registry-driven voting while
preserving:

- strategy order
- vote dictionaries
- BUY/SELL/HOLD counts
- minimum two-vote requirement
- HOLD vote-strength behavior
- response keys

## Compatibility layer

`app/strategy_executor.py`

The legacy helper functions remain available:

- `execute_rsi_pullback()`
- `execute_ma_alignment()`
- `execute_breakout()`
- `execute_trend_following()`

They are thin wrappers around plugins. This preserves existing imports while the
plugin package owns strategy behavior.

## Safety guarantees

Sprint 1A intentionally does not change:

- strategy thresholds
- numeric parsing
- signal values
- reason strings
- market-regime blocking
- strategy aliases
- unknown-strategy fallback
- four-strategy voting membership
- selected RSI `< 30` behavior
- live-signal response contracts

## Adding a future strategy

A new strategy should:

1. Implement the Strategy protocol.
2. Declare immutable StrategyMetadata.
3. Return StrategyDecision.
4. Add focused boundary tests.
5. Be registered explicitly for voting and/or execution.
6. Pass registry capability validation.
7. Avoid changing existing registry order unless explicitly approved.

## Next architectural step

Sprint 1B should evolve `MarketContext` from a thin compatibility wrapper into a
validated multi-market, multi-timeframe context while preserving the strategy
plugin interface established here.
