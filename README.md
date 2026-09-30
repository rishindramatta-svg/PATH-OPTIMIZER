# PNG9 — Personalized Learning Path Optimizer

PNG9 is an adaptive learning platform for Python foundations. It records a student's answers and confidence, estimates concept mastery with Bayesian Knowledge Tracing (BKT), detects misconception evidence and suspicious response patterns, and updates a personalized practice path with an explanation. Instructors view enrolled course cohorts; administrators review operational signals, flagged answers, and simulator results.

## Screenshots

The design references are in [`design/`](design/) and the screen-by-screen comparison inventory is in [`docs/visual-audit.md`](docs/visual-audit.md). No fresh end-to-end demo screenshots were captured in this documentation pass because the browser automation session stopped before it could verify the active page.

## Quickstart (three commands)

Use two terminals from the repository root. Python 3.11+ and Node.js 20+ are required. SQLite is created locally by default and the API seeds demo data on startup.

```powershell
# 1 — install backend dependencies
cd backend; python -m pip install -e ".[dev]"
```

```powershell
# 2 — start the API (terminal 1)
cd backend; python -m uvicorn app.main:app --reload
```

```powershell
# 3 — install and start the frontend (terminal 2)
cd frontend; pnpm install; pnpm dev
```

Open <http://localhost:5173>. API docs are at <http://localhost:8000/docs>; health at `/health`; Prometheus metrics at `/metrics`.

## Demo accounts

The backend seeds the three local roles on startup. The default development password is **`DemoPass123!`** for all three; override it before startup with `DEMO_PASSWORD`. These credentials are for local demos only.

| Role | Email |
|---|---|
| Student | `student@png9.local` |
| Instructor | `instructor@png9.local` |
| Admin | `admin@png9.local` |

You can also register a new student from the login screen. The local instructor can enroll a student into the Python Foundations cohort.

## Environment variables

| Variable | Purpose | Default / local behavior |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database connection | `sqlite:///./png9.db`; PostgreSQL URLs are supported but not live-verified here. |
| `SECRET_KEY` | JWT signing key | Development fallback only; set a unique value for any deployed environment. Production requires at least 32 characters and rejects placeholders. |
| `ENV` / `APP_ENV` | Runtime environment | Development. Set `ENV=production` for production checks. |
| `COOKIE_SECURE` | Add Secure cookie flag and HSTS | False in local HTTP; production requires `true` and HTTPS. |
| `CORS_ORIGINS` | Credentialed browser origin allowlist | `http://localhost:5173`; comma-separated origins. Wildcard is rejected. |
| `REDIS_URL` | Shared cache, rate limits, SSE fan-out | Optional; process-local fallback logs when unavailable. |
| `DEMO_PASSWORD` | Seeded account password | `DemoPass123!` (development only). |
| `LLM_PROVIDER`, `LLM_API_KEY` | Optional misconception-analysis provider | Not required; deterministic rule fallback works without a key. |
| `VITE_API_URL` | Optional frontend API origin override | Same-origin Vite proxy to `localhost:8000` in development. |

## Tests, lint, type-check, and build

From `backend/`: `python -m pytest -q`; `ruff check app tests scripts locustfile.py loadtest alembic`; `ruff format --check app tests scripts locustfile.py loadtest alembic`.

From `frontend/`: `pnpm test`; `pnpm run typecheck`; `pnpm run lint`; `pnpm run build`.

Current detailed results and limitations are in [evaluation](docs/evaluation.md), [load test](docs/load-test.md), and [roadmap](docs/roadmap.md). The load test uses a local SQLite file; its 50-user run showed substantial timeout/error rates and is not a production throughput claim.

## Documentation

- [Requirements (SRS)](docs/SRS.md)
- [Architecture and data flow](docs/architecture.md)
- [API reference](docs/API.md) · generated [OpenAPI schema](docs/openapi.json)
- [ER diagram](docs/data-model.md) · generated from SQLAlchemy models by `backend/scripts/generate_docs.py`
- [Tech stack rationale](docs/tech-stack.md) · [Security notes](docs/security.md)
- [Design system](docs/design-system.md) · [Visual audit](docs/visual-audit.md)
- [Evaluation simulator](docs/evaluation.md) · [Load test](docs/load-test.md)
- [Roadmap by level](docs/roadmap.md)

## Known operational limits

Redis-off fallbacks are process-local; PostgreSQL and Docker Compose were not verified against live services in this environment. The adaptive-vs-static simulator is synthetic and does not constitute evidence from real classrooms. See [security notes](docs/security.md) for deployment constraints.
