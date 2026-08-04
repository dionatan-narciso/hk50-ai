# HK50 AI Architecture

## Purpose

HK50 AI is a React and FastAPI trading-research platform. The current system supports HK50 market analysis, research-driven signals, paper trade tracking, historical replay, learning memories, risk controls and a web dashboard.

Sprint 0 established two architectural rules:

1. Trading behaviour must remain reproducible and testable.
2. Replay, paper and future funded-live state must never share mutable files.

## Repository layout

```text
hk50-ai/
├── .github/workflows/          Automated backend checks and tests
├── backend/
│   ├── app/                    FastAPI application and trading services
│   │   └── research/           Modular Research Director
│   ├── data/                   Default runtime data root
│   │   ├── paper/              Paper-trading state and learning memory
│   │   ├── replay/             Historical replay state and learning memory
│   │   └── live/               Reserved for future funded-live state
│   ├── scripts/                Environment, architecture and dead-code audits
│   ├── tests/                  Backend regression tests
│   ├── requirements.txt        Python dependencies
│   └── replay_*.py             Replay analysis and learning services
├── frontend/                   React and Vite dashboard
└── docs/                       Architecture and developer documentation
```

## Application entry points

### Backend

The FastAPI application is created in:

```text
backend/app/main.py
```

Development startup:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

The backend exposes API routes for research labs, signal generation, paper tracking, journals, replay, analytics, risk and learning summaries.

### Frontend

The React application is started by Vite from the `frontend` package:

```powershell
cd frontend
npm install
npm run dev
```

The default development URL is:

```text
http://localhost:5173
```

## Runtime state boundaries

`backend/app/runtime_paths.py` is the authority for mutable runtime paths.

The root can be overridden with:

```text
HK50_DATA_DIR
```

Default layout:

```text
backend/data/
├── paper/
├── replay/
└── live/
```

### Paper state

Paper state includes:

- open position and last-signal state
- canonical paper trade journal
- strategy performance memory
- voting performance memory
- quality performance memory
- confidence calibration memory
- regime performance memory
- paper entry-learning memory
- saved research results

Paper consumers must not read replay files or unscoped legacy files.

### Replay state

Replay state includes:

- replay trade journal
- replay learning memory
- entry-context learning state
- adaptive entry weights
- replay learning-controller state

Replay services must not create or modify paper state.

### Future funded-live state

The `live/` runtime namespace is reserved for future real-money execution. Paper files must not be re-used for funded trading.

## End-to-end trading flow

```text
Market data
    ↓
Indicators and market context
    ↓
Market and volatility regime detection
    ↓
Strategy execution and strategy voting
    ↓
Research Director context
    ↓
Confidence adjustments and quality scoring
    ↓
Position sizing and daily risk controls
    ↓
Automatic paper signal tracker
    ↓
Canonical paper journal
    ↓
Analytics, equity, learning memories and dashboards
```

## Research architecture

Production imports use:

```text
backend/app/research/director.py
```

The director is an orchestrator rather than a monolith:

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

### Responsibilities

- `source_loader.py`: calls research labs, research memory, trade analytics and canonical paper performance storage.
- `live_performance.py`: ranks paper strategy records and calculates the established live score.
- `candidate_ranker.py`: creates and orders strategy candidates, applies analytics bonuses and the existing live override.
- `confidence_scorer.py`: calculates the Research Director confidence score and label.
- `recommendation_builder.py`: builds the existing human-readable recommendations.
- `director.py`: assembles the final response without direct CSV or research-lab I/O.
- `research_results_repository.py`: owns saved research-lab result persistence.

`backend/app/research_engine.py` now contains only active research labs, backtest helpers and the research-memory compatibility surface. The obsolete monolithic Research Director and duplicate journal functions have been removed.

## Paper journal architecture

Canonical storage:

```text
<HK50_DATA_DIR>/paper/trade_journal.csv
```

Owner:

```text
backend/app/paper_trade_journal_repository.py
```

The repository normalises both historical naming conventions, including:

```text
result_pct / return_percent
timestamp / closed_at
strategy / reason
direction / signal
```

Consumers include:

- trade-journal API
- automatic signal tracker
- trade analytics
- daily risk manager
- equity curve
- live learning feed

A tracker-closed trade is written once by the canonical tracker path. Compatibility callbacks must not write a second journal row.

## Replay architecture

Replay writes through:

```text
backend/app/replay_journal_repository.py
```

Replay readers and specialised analyses resolve the configured replay journal rather than the paper journal. Entry learning and adaptive tuning also resolve replay-scoped memory paths.

## Validation and CI architecture

Run locally from `backend/`:

```powershell
python scripts/check_environment.py
python scripts/audit_architecture.py
python scripts/audit_dead_code.py
python -m unittest discover -s tests -v
```

GitHub Actions workflow:

```text
.github/workflows/backend-tests.yml
```

CI installs backend dependencies, compiles Python files, validates the environment, audits architecture boundaries, runs the advisory dead-code scan and executes the complete unit-test suite with a temporary `HK50_DATA_DIR`.

The dead-code audit is intentionally advisory. It identifies candidates for human review and fails only for parse errors.

## Architectural constraints

1. Do not add hardcoded `data/...` paths to trading modules.
2. Do not allow replay code to read or write paper state.
3. Do not use paper state for future funded-live execution.
4. Do not duplicate journal writers.
5. Preserve current trading behaviour during architecture-only changes.
6. Add regression tests before or with each extraction.
7. Keep `director.py` as orchestration; put deterministic rules in pure modules.
8. Never delete dead-code candidates without confirming all runtime, API and test references.
