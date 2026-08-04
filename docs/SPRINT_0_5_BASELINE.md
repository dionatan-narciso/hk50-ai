# Sprint 0.5 Baseline

## Status

Sprint 0.5 establishes the hardened engineering baseline for HK50 AI before any behaviour-changing Sprint 1 work begins.

The platform now has explicit runtime-state boundaries, canonical repositories, modular research orchestration, regression coverage for critical trading paths and automated architecture checks.

## Baseline architecture

### Application entry points

- Backend: `backend/app/main.py`
- Backend startup: `python -m uvicorn app.main:app --reload --port 8000`
- Frontend: React/Vite under `frontend/`
- Frontend startup: `npm run dev`

### Runtime state ownership

`backend/app/runtime_paths.py` is the authority for mutable runtime files.

```text
backend/data/
├── paper/
├── replay/
└── live/
```

Paper and replay state are isolated. The live namespace is reserved for future funded execution and must not reuse paper files.

### Research architecture

The production Research Director is modular:

```text
source_loader.py
    ↓
live_performance.py
    ↓
candidate_ranker.py
    ↓
confidence_scorer.py
    ↓
recommendation_builder.py
    ↓
director.py
```

`research_engine.py` now owns only active research labs, backtest helpers and research-memory compatibility. The obsolete monolithic director and duplicate journal functions have been removed.

### Canonical state repositories

Canonical owners include:

- `paper_trade_journal_repository.py`
- `replay_journal_repository.py`
- `research/research_results_repository.py`
- strategy, voting, quality, confidence, regime and entry-learning memories resolved through `RuntimePaths`

## Safety controls

The baseline includes:

- Replay-to-paper state isolation
- Canonical paper and replay journals
- No duplicate paper journal writers
- Configurable `HK50_DATA_DIR`
- Generated/runtime state excluded from Git
- Environment validation before tests
- Architecture-boundary audit
- Advisory dead-code audit
- GitHub Actions CI

## Critical-path coverage

Characterisation and regression tests protect:

- Live signal generation
- Confidence adjustment ordering
- Voting effects and forced HOLD decisions
- Position sizing boundaries and rejection conditions
- Daily trade, loss and drawdown limits
- Paper journal contracts
- Replay journal and learning isolation
- Research source loading
- Candidate ranking
- Confidence scoring
- Recommendation generation
- Runtime path resolution
- Strategy, quality, voting, confidence, regime and entry-learning memories

## Standard validation workflow

Run from `backend/`:

```powershell
python scripts/check_environment.py
python scripts/audit_architecture.py
python scripts/audit_dead_code.py
python -m unittest discover -s tests -v
```

The dead-code audit is advisory. Parse failures are errors; candidate findings require human review before removal.

## Behaviour-preservation statement

Sprint 0 and Sprint 0.5 were architecture and safety sprints. They were not intended to optimise strategy profitability or intentionally change entry, exit, confidence, sizing or risk rules.

Any Sprint 1 behaviour change must:

1. State the intended trading change explicitly.
2. Add or update tests that describe the new behaviour.
3. Compare results against this baseline.
4. Keep paper, replay and future live state isolated.

## Known limitations carried into Sprint 1

- The system remains HK50-focused.
- Strategy implementations are not yet plugins.
- Market configuration is not yet abstracted.
- Research labs still live in `research_engine.py`.
- CSV remains the primary local persistence mechanism.
- Replay and paper results do not yet represent funded-live execution evidence.
- The dead-code audit is static and may report false positives.

## Sprint 0.5 exit checklist

- [x] Architecture documentation exists.
- [x] Developer workflow is documented.
- [x] Runtime paths are centralised.
- [x] Paper and replay state are isolated.
- [x] Canonical journals and memories are in place.
- [x] Research Director is modular.
- [x] Obsolete monolithic director and duplicate journal functions are removed.
- [x] Critical signal and risk paths have characterisation tests.
- [x] Environment and architecture checks run in CI.
- [x] Dead-code candidates can be generated reproducibly.
- [ ] Review the current dead-code audit output and approve any final removals.
- [ ] Record the final passing test count and audit output.

Once the final two items are recorded, Sprint 0.5 can be formally closed and Sprint 1 can begin from this baseline.
