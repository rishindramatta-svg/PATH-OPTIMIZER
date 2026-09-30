# Technology choices

- **React 18 + TypeScript + Vite**: fast local feedback and typed, component-based browser UI.
- **FastAPI + Pydantic**: Python-first API with request validation and generated OpenAPI docs.
- **SQLAlchemy 2 + SQLite**: relational persistence with a low-friction local fallback; PostgreSQL deployment configuration is future work.
- **BKT + rule-based feedback**: transparent deterministic learning updates work without a provider key and are straightforward to test.
- **Zod + TanStack Query**: runtime validation at API boundaries and a cache layer for the browser.

The stack follows the supplied brief where feasible; features still absent from this working slice are called out in `roadmap.md`.
