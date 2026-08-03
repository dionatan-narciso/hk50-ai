# HK50 AI Developer Guide

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Useful frontend commands:

```powershell
npm run lint
npm run build
npm run preview
```

## Runtime data configuration

Mutable state defaults to `backend/data`. To isolate a development or test run, set:

```powershell
$env:HK50_DATA_DIR = "$PWD\tmp-data"
```

The application separates state by execution mode:

```text
<root>/paper
<root>/replay
<root>/live
```

Never point two execution modes at the same mutable file.

## Change workflow

For every architecture or trading change:

1. Inspect all readers and writers of the affected state or function.
2. Add characterization tests for existing behaviour.
3. Make the smallest coherent change.
4. Run the full backend suite.
5. Check that no paper, replay or live boundary was crossed.
6. Commit with a narrow, descriptive message.

Architecture-only batches must not alter strategy thresholds, signal rules, exit rules, risk limits or position-sizing formulas.

## Adding a Research Director component

Pure Research Director logic belongs in:

```text
backend/app/research/
```

A component should:

- accept dictionaries, mappings or sequences as explicit inputs
- return a deterministic dictionary or list
- avoid reading CSV files directly
- avoid importing FastAPI routes
- avoid writing mutable state
- have threshold and boundary tests

Runtime source collection belongs in `source_loader.py`. Final orchestration belongs in `director.py`.

## Adding or changing a runtime file

1. Add the path to `backend/app/runtime_paths.py`.
2. Place the file under the correct mode directory.
3. Give one module ownership of reading and writing it.
4. Migrate all direct readers and writers together.
5. Add tests proving legacy and other-mode files are ignored.
6. Use `HK50_DATA_DIR` in tests so repository data is untouched.

Do not introduce code such as:

```python
pd.read_csv("data/example.csv")
```

Resolve the path through `RuntimePaths` or the repository/service that owns the file.

## Adding a strategy during Sprint 1

The current strategy system is not yet a formal plugin framework. Until that framework is introduced:

- preserve the strategy executor contract
- preserve the strategy-voting response contract
- document every new strategy name
- add deterministic signal tests
- add regime-compatibility tests
- do not change existing strategy names silently because memories and journals group by those names

The planned plugin interface should expose a consistent result containing at least:

```text
strategy name
signal
reason
confidence or score context
market regime context
risk metadata
```

The final interface must be based on the actual existing executor contract before implementation.

## Adding a market during Sprint 1

Do not duplicate HK50 modules and rename the symbol. A market abstraction should explicitly define:

- market identifier and data symbol
- timezone and trading sessions
- price precision and tick conventions
- supported data intervals
- market-specific filters
- execution and contract assumptions

Market-independent indicators, strategies, voting, research and risk services should consume a market context rather than hardcoding HK50.

## Journal rules

The canonical paper journal owner is:

```text
backend/app/paper_trade_journal_repository.py
```

New paper trade closures must go through this owner. Do not create an additional CSV writer in an API route, tracker callback or analytics module.

The replay journal owner is:

```text
backend/app/replay_journal_repository.py
```

Replay and paper journals must remain independent.

## Testing guidance

Prefer tests that assert behaviour or architecture rather than exact formatting. For source-wiring tests, use Python's `ast` module instead of brittle string splitting.

Critical test categories:

- runtime path isolation
- paper/replay contamination protection
- journal schema normalization
- scoring threshold boundaries
- strategy candidate ordering
- confidence labels
- risk-limit boundaries
- open-position persistence
- API wiring

## Pull-request checklist

- [ ] Full backend suite passes
- [ ] Frontend lint/build passes when frontend changed
- [ ] No new hardcoded mutable paths
- [ ] No secrets or runtime CSV files added
- [ ] No trading behaviour changed unintentionally
- [ ] New behaviour is documented
- [ ] Rollback path is clear for core changes
