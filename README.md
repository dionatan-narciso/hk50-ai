# HK50 AI Trading Platform

HK50 AI is a React and FastAPI trading-research platform for market analysis, research-driven signals, paper trading, historical replay, learning memories and risk management.

The current production focus is HK50. The architecture is being prepared for future strategy plugins, multiple markets and portfolio-level risk without changing existing trading behaviour prematurely.

## Current engineering baseline

- FastAPI backend and React/Vite frontend
- Modular Research Director
- Paper and replay state isolation
- Canonical paper and replay journals
- Configurable runtime data root
- Automated backend regression tests
- GitHub Actions backend CI

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Sprint 0.5 Inventory](docs/SPRINT_0_5_INVENTORY.md)

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
uvicorn app.main:app --reload --port 8000
```

The backend is available at:

```text
http://localhost:8000
```

## Frontend setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend is available at:

```text
http://localhost:5173
```

## Runtime data isolation

Mutable state defaults to:

```text
backend/data/
├── paper/
├── replay/
└── live/
```

Override the root for development or tests with:

```powershell
$env:HK50_DATA_DIR = "$PWD\tmp-data"
```

Paper, replay and future funded-live execution must never share mutable state files.

## Research Director

Production code uses:

```text
backend/app/research/director.py
```

Its responsibilities are decomposed into source loading, live-performance ranking, candidate ranking, confidence scoring and recommendation building. The legacy implementation in `research_engine.py` remains temporarily for rollback and research-lab compatibility.

## Development principle

Architecture and safety come before profitability optimization. Each change should be small, reviewable, tested and behaviour-preserving unless a trading change is explicitly approved.
