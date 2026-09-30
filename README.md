# Personalized Learning Path Optimizer (PNG9)

Adaptive learning app that models concept mastery and confidence, identifies misconceptions, and adapts practice recommendations.

## Current status
Initial working slice. No design PNGs were supplied: `Untitled.zip` contains `error-card.png` and `error-card@2x.png` only. The interface uses a responsive default design until screen references are available. Authentication hardening/RBAC, instructor/admin views, WebSockets, LLM analysis, evaluation, Kubernetes and CI/monitoring remain incomplete; see [`docs/roadmap.md`](docs/roadmap.md).

## Quick start
1. Backend: `cd backend; python -m pip install -e .; python -m uvicorn app.main:app --reload`
2. Frontend: `cd frontend; npm install; npm run dev` (set `VITE_API_URL=http://localhost:8000` if needed).
3. Open the Vite URL; API docs are at `http://localhost:8000/docs`. Use the Practice item, answer confidently incorrectly, and the API returns repair feedback and a path reason.

## Verification
- Frontend: `npm run build`, `npm test`
- Backend: `python -m pip install -e '.[dev]'`, then `python -m pytest`
