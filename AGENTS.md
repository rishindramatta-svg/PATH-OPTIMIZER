# PNG9 project notes

## Stack and commands
- Frontend: React 18, Vite, TypeScript.
- Backend: Python 3.11+ and FastAPI; SQLite for local development.
- Frontend commands: `npm install`, `npm run dev`, `npm run build`, `npm test`.
- Backend commands: `python -m pip install -e .`, `python -m uvicorn app.main:app --reload`, `python -m pytest`.

## Layout
- `frontend/`: browser application.
- `backend/app/`: API, persistence, learning logic, seed data.
- `design/`: visual references, when supplied.
- `docs/`: architecture and product documentation.

## Decisions
- The `/design` directory contains 15 PNG references: 11 desktop screens and 4 mobile screens. Inventory and sampled design tokens are documented in `docs/design-system.md`; compare each implemented screen at desktop/mobile breakpoints against its matching PNG when changing shared UI.
- Visual references are 2880 px wide for desktop and 780 px wide for mobile. Their typography appears to use Inter; retain a system sans fallback because the images do not contain font metadata.
- Local development should work without an LLM key; deterministic learning logic is the default.
- The current working slice seeds 25 concepts and 60 questions, applies BKT plus a learning transition, and uses explicit `timeTakenMs < 2000` anomaly handling.
- Path selection prioritizes active misconception repairs, then mastered concepts due for spaced review (7 days after last interaction, or 14 days at mastery ≥0.90), then prerequisite-ready practice; challenge is the final fallback. The simulator calls this same path function.
- Authentication uses bcrypt, HTTP-only access/refresh cookies, refresh rotation/revocation, protected routes, role checks, and user-bound learner records. Development-only SECRET_KEY fallback and demo credentials must be replaced for deployment. CORS origins are configured with CORS_ORIGINS; production startup requires a non-placeholder SECRET_KEY and COOKIE_SECURE=true. Admin actions are audited.
- Local demo accounts are student@png9.local, instructor@png9.local, and admin@png9.local; development seed password defaults to DemoPass123! and can be overridden with DEMO_PASSWORD. Never use these defaults in deployed environments.
- Learning APIs and analytics are DB-backed. SSE is authenticated and publishes path_updated, misconception_detected, mastery_updated, and anomaly_flagged. Reconnection uses client exponential backoff.
- Adversarial handling identifies fast answers, rapid wrong streaks, and repeated-option patterns; flagged responses are down-weighted in BKT. Confidence is reflected against observed performance. Redis provides shared cache/rate/event state when configured; in-process fallback logs a warning when Redis is unavailable.
- SQLite is the local default; PostgreSQL is supported through `DATABASE_URL`. Alembic migrations run at backend startup and target both dialects. Hot user/time and user/concept indexes are maintained in migrations.
- Evaluation simulator command: from `backend/`, run `python -m app.evaluation.run --seeds 30`; it compares equal 120-interaction budgets across 30 paired seeds/profile and records held-out transfer results plus paired 95% confidence intervals in `docs/evaluation.md`. It is a synthetic model, not classroom evidence.
- Local API load test command: after starting the API with a disposable database, run `python -m loadtest.run --users 50 --ramp 10 --duration 60 --provision`. It creates isolated per-user accounts so the production rate limiter remains on. Latest SQLite stress figures and limitations are in `docs/load-test.md`; high contention caused timeouts/errors, so use PostgreSQL for capacity work.
- Lint commands: `ruff check app tests scripts locustfile.py loadtest alembic` from `backend/`, and `pnpm run lint` from `frontend/`. Frontend lint currently checks recommended TypeScript rules and unused variables; explicit `any` is temporarily disabled because the existing API view models are being typed incrementally.
- Frontend verification commands are `pnpm run typecheck`, `pnpm test`, and `pnpm run build` from `frontend/`; backend tests are `python -m pytest -q` from `backend/`.
- CI configuration runs backend/frontend lint, tests, type-check, build, and Docker image builds. Grafana and Kubernetes templates are under `deploy/`.
- Current product and deployment requirements are in `docs/SRS.md`; architecture, API, and data-model diagrams are in `docs/architecture.md`, `docs/API.md`, and `docs/data-model.md`.
- Regenerate the OpenAPI JSON/API reference and ER diagram from the FastAPI application and SQLAlchemy models with `cd backend; $env:PYTHONPATH='.venv-packages'; python scripts/generate_docs.py`. The generated outputs are `docs/openapi.json`, `docs/API.md`, and `docs/data-model.md`; do not edit those outputs manually without rerunning the generator.
- `docs/roadmap.md` is the authoritative L1–L4 status table; deployment/security caveats belong in `docs/security.md`. Do not describe SQLite load results as production capacity or simulator results as classroom evidence.
- `docs/visual-audit.md` records known differences against all design PNGs. A claimed final pixel-level comparison requires fresh browser captures; document any blocked browser verification plainly.
- `README.md` is the public quickstart and demo credential entry point. Demo passwords are local-only; never introduce real secrets into the docs or repository.
