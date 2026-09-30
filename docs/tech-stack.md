# Technology choices

| Area | Choice | Rationale |
|---|---|---|
| Browser | React 18, TypeScript, Vite | Component-based UI, typed client logic, quick local iteration and production static assets. |
| UI styling | Tailwind theme plus shared CSS custom properties | Central design tokens and responsive screen compositions mapped to the supplied PNG references. |
| API | FastAPI + Pydantic | Typed request/response validation, generated OpenAPI, async-compatible SSE, and straightforward Python integration with the learning logic. |
| Persistence | SQLAlchemy 2 + Alembic; SQLite default, PostgreSQL selectable by `DATABASE_URL` | One model/migration layer across local use and a production database. PostgreSQL has not yet been verified against a live server in this workspace. |
| Mastery | Bayesian Knowledge Tracing (BKT), weighted for suspicious events | Interpretable per-concept probability updates; quick/patterned responses contribute less evidence. It is a heuristic learning estimate, not a calibrated student diagnosis. |
| Live updates | Server-Sent Events (SSE) | Events only flow server-to-browser; answer submissions and commands already use REST. SSE uses standard HTTP, integrates with browser `EventSource`, and works through common HTTP proxies. A bidirectional WebSocket would add connection complexity without a current client-to-server event requirement. Client reconnect uses exponential backoff. |
| Shared state | Optional Redis for cache, rate state and event fan-out; process-local fallback | Redis can share state between API workers. Local fallback keeps development usable but is not cross-process consistent. |
| Tests | pytest, Vitest, ESLint, TypeScript, Ruff | Backend rules and routes plus frontend UI logic are checked in their respective ecosystems. |
| Operations | Prometheus endpoint, Grafana dashboard JSON, Compose/Kubernetes templates | Gives a deployment starting point. Container orchestration and a live PostgreSQL deployment remain unverified. |
| Evaluation/load | Fixed-seed synthetic simulator; asyncio + httpx load driver | Makes assumptions and local contention reproducible; results are explicitly not classroom or production evidence. |

See [security notes](security.md) for configuration constraints and known operational limitations.
