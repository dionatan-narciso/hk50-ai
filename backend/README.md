# HK50 AI Terminal Backend

Phase 1 backend shell. It serves sample market data to the React terminal.

Run:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open API health check:

```text
http://localhost:8000/health
```
