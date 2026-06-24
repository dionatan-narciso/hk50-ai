# HK50 AI Terminal Phase 1

This is the first React + FastAPI version of the HK50 AI Assistant.

Goal of this phase:

1. Keep the existing Python trading work safe.
2. Build the professional mockup style frontend in React.
3. Use FastAPI as the bridge between the UI and your AI engine.
4. Start with realistic sample data so the visual design can be built quickly.
5. In Phase 2, connect the existing Streamlit logic into backend endpoints.

## Run backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Important

Your current Streamlit app is not replaced. This is the new professional frontend phase.
The existing trading logic will be migrated into the backend step by step.
