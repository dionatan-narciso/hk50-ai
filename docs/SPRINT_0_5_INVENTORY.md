# Sprint 0.5 Inventory

## Objective

Sprint 0.5 prepares the repository for strategy and market extensibility without changing trading behaviour.

This inventory records the current architectural position, known legacy boundaries and the recommended cleanup order.

## Current stable foundations

### State and reproducibility

- Runtime paths are centralized in `app/runtime_paths.py`.
- Paper and replay mutable state are separated.
- The paper trade journal has one canonical repository.
- Replay has a separate canonical journal repository.
- Paper open-position and signal state use configured paper paths.
- Strategy, voting and quality paper memories use configured paper paths.
- CI runs backend tests with a temporary data root.

### Research Director

Production consumers import `app.research.director.run_research_director`.

The modular director is decomposed into:

- `source_loader.py`
- `live_performance.py`
- `candidate_ranker.py`
- `confidence_scorer.py`
- `recommendation_builder.py`
- `director.py`

The modular result builder is deterministic when supplied fixed inputs.

## Dependency map

```text
app.main
├── app.live_signal_engine
│   └── app.research.director
│       ├── app.research.source_loader
│       │   ├── app.research_engine research labs and memory
│       │   ├── app.trade_analytics
│       │   └── app.live_performance_memory
│       ├── app.research.live_performance
│       ├── app.research.candidate_ranker
│       ├── app.research.confidence_scorer
│       └── app.research.recommendation_builder
├── app.automatic_signal_tracker
│   └── app.paper_trade_journal_repository
├── app.daily_risk_manager
│   └── app.paper_trade_journal_repository
├── app.equity_curve
│   └── app.paper_trade_journal_repository
└── replay endpoints
    ├── app.replay_journal_repository
    ├── replay learning services
    └── specialised replay analyses
```

## Known legacy or transitional areas

### `app/research_engine.py`

Status: active for research labs and memory, transitional for the old director and older journal helpers.

Risks:

- large module with multiple responsibilities
- legacy `run_research_director()` remains available
- older journal helper definitions may still exist even though production API wiring uses the canonical repository
- future edits can accidentally reintroduce direct file access

Recommended action:

1. Add tests proving production code does not import the legacy director or journal helpers.
2. Mark legacy functions as deprecated in code documentation.
3. Remove them only after confirming no remaining callers.
4. Later split research labs and research memory into dedicated modules.

### Strategy execution and voting

Status: functional but not yet a plugin architecture.

Risks:

- strategy names are data identifiers used by journals and memories
- strategy dispatch may require central edits for every new strategy
- market-specific assumptions may be embedded in execution logic

Recommended action:

- characterize the existing executor and voting contracts before designing a plugin interface
- preserve strategy names during migration
- introduce a registry before adding many new markets or strategies

### Market specificity

Status: HK50-focused.

Risks:

- symbol, session and market assumptions may be distributed across data, signals and UI
- copying modules for new markets would create divergence

Recommended action:

- inventory every hardcoded `HK50`, ticker, timezone and session assumption
- define a market-context contract
- migrate one reader at a time without changing HK50 results

### Remaining mutable memories

Status: strategy, voting and quality memory are isolated; regime and confidence calibration require final verification and, where necessary, migration.

Recommended action:

- inspect `regime_analytics.py` and `confidence_calibration_memory.py`
- identify every reader and writer
- add `RuntimePaths` entries where absent
- migrate each memory atomically with isolation tests

### Frontend quality gates

Status: Vite provides lint and build commands; backend CI is currently the established automated gate.

Recommended action:

- add frontend lint and build to CI after confirming the current frontend passes locally
- avoid blocking backend work on unrelated historical frontend lint debt without first documenting it

## Generated and local files that must remain untracked

The repository should not track:

- `.env` and local secret files
- Python virtual environments
- `__pycache__/` and `*.pyc`
- test caches and coverage output
- `node_modules/`
- frontend build output
- editor and operating-system files
- runtime CSV/JSON state under paper, replay or live directories unless an explicit sanitized fixture is intended
- temporary `HK50_DATA_DIR` folders

Sprint 0.5 should verify `.gitignore` covers these categories.

## Coverage review priorities

Existing tests strongly cover state boundaries and modular Research Director rules. The next critical-path coverage should target:

1. live signal generation with fixed dependencies
2. position sizing boundaries
3. daily risk thresholds
4. automatic tracker exit conditions
5. strategy executor dispatch
6. strategy-voting outcomes
7. market and volatility regime classification
8. frontend build and API contract smoke tests

## Recommended Sprint 0.5 order

### Batch 0.5A — Documentation

- architecture document
- developer guide
- dependency and legacy inventory
- README refresh

### Batch 0.5B — Repository hygiene

- audit and strengthen `.gitignore`
- identify tracked runtime/generated files
- add an environment-check script

### Batch 0.5C — Remaining state audit

- regime memory isolation
- confidence calibration isolation
- tests for all remaining mutable state

### Batch 0.5D — Legacy cleanup

- locate remaining callers of legacy Research Director and journal helpers
- deprecate or remove unused compatibility code
- preserve research-lab behaviour

### Batch 0.5E — Coverage and CI expansion

- add tests for critical signal, risk and tracker paths
- add frontend lint/build to CI when green
- document the Sprint 1 baseline

## Exit criteria for Sprint 0.5

Sprint 0.5 is complete when:

- architecture and setup are accurately documented
- mutable files are scoped by execution mode
- generated files and secrets are excluded
- legacy compatibility code has an explicit status and no hidden production callers
- critical untested paths have an agreed test plan
- backend CI is green
- the repository is ready for strategy and market interfaces without behavioural changes
