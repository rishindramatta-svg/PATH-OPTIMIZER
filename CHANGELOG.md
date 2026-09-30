# Changelog

## Unreleased
- Diagnosed the original adaptive-vs-static evaluation flaws and replaced practiced-state gain with same-seed held-out pre/post assessment; both strategies now have equal interaction budgets. The separate synthetic learner includes held misconceptions and lower-efficacy ordinary feedback vs targeted repair. Generated 30-paired-seed/profile means and approximate 95% CIs, documented path-priority limitations and mixed results in `docs/evaluation.md`.
- Closed the identified path-priority gap with real interaction-timestamp-based spaced review: repairs first, due mastered-concept reviews next (7/14-day mastery-dependent interval), then prerequisite-ready practice, with challenge fallback. Added optimizer-order tests.
- Added the dependency-light asyncio + httpx load runner at `backend/loadtest/run.py`, with per-user test accounts, limiter-safe pacing, and login/path/answer/analytics workload. Recorded the 50-VU/60-second SQLite result and its high timeout/error rate in `docs/load-test.md`.
- Installed Ruff into ignored local tooling, configured the dev dependency, linted and fixed backend Python sources. Added ESLint/TypeScript ESLint config and a frontend lint script, and added both lint checks to CI.
- Added/updated simulator tests for reproducibility, held-out metric reporting, and 30-seed confidence intervals.
- Verification on 2026-10-01: backend **25 tests passed**; Ruff backend lint passed; frontend **20 tests passed**, ESLint passed, TypeScript type-check passed, and Vite production build passed. The local SQLite load run completed but reported 31.42% errors and p95 31.98s under 50 VUs; see `docs/load-test.md`. Docker/PostgreSQL production runtime checks were outside this task.
- Completed remaining data-backed UI gaps: analytics period query (`7d`/`30d`/all), server-side misconception status/severity filters, observed-data dashboard difficulty and time estimates, removed nonfunctional social/policy links, misconception-specific repair examples/questions, instructor course enrollment and course-scoped cohorts, and simulator output on Admin/Ops.
- Added 17 frontend UI-logic tests for fast-answer confirmation, confidence reflection, route roles, SSE reconnect backoff, and analytics/tracker filters (20 frontend tests total).
- Added the initial seeded adaptive-vs-static simulator using shared BKT, anomaly, misconception, and path logic. It was superseded by the held-out, multi-seed methodology documented above.
- Added `DATABASE_URL` PostgreSQL support, portable Alembic migrations and hot indexes; optional Redis caching, rate limiting and SSE fan-out with local fallback; request-ID JSON logs and Prometheus `/health`/`/metrics`; Grafana dashboard; Docker Compose, Kubernetes templates, and CI workflow.
- An earlier Locust attempt was blocked by Windows native dependencies. It has been superseded by the dependency-light asyncio + httpx runner and measured result documented above.
- Previous design/security-pass verification (before these evaluation and load-test changes): backend 24 tests passed; frontend 20 tests passed, type-check passed, and production build passed. Compose and Kubernetes YAML parsed. Docker was unavailable, so container builds and Compose startup were not verified. A live PostgreSQL service was unavailable; PostgreSQL DDL compilation and SQLite migrations were verified.
- Scaffolded a React/TypeScript + Vite frontend and FastAPI + SQLAlchemy backend.
- Added a responsive student dashboard, knowledge graph explorer, adaptive practice view, confidence slider, misconception repair feedback, offline/error states, and default design tokens.
- Seeded a 25-concept Python prerequisite chain with 60 practice questions and wrong-answer misconception tags; reject prerequisite cycles during seeding.
- Added BKT mastery updates, confidence calibration labels, fast-answer exclusion, misconception severity updates, and a prerequisite-aware next-step API.
- Added bcrypt password hashing and HTTP-only JWT access/refresh cookie endpoints with login, registration, refresh, and current-user routes.
- Added architecture/API/requirements/roadmap notes, local Dockerfiles, and a Compose setup.
- Verified frontend production build and 3 frontend unit tests; backend tests cover BKT, cycle rejection, and the wrong/confident answer flow.
- Design screen fidelity was unverified before the `/design` assets were added; see the 2026-09-30 entry for the completed screen implementation and comparison pass.

## 2026-09-30 — Design implementation
- Inventoried and inspected all 15 `/design` PNGs (11 desktop and 4 mobile), documenting each screen and sampled colors, typography, spacing, radii, and shadows in `docs/design-system.md`.
- Added the reference palette, Inter-first font stack, spacing additions, and card/panel/control/tag/pill radii and shadows to the Tailwind theme; mirrored tokens are used by shared CSS components.
- Reworked the React UI for Login/Register, Student Dashboard, Knowledge Graph, Practice Session, Misconception Repair, Learning Path, Misconception Tracker, Analytics, Instructor, Admin/Ops, and edge-case states, with responsive layouts.
- Added analytics, instructor overview, admin metrics/flags, and logout API support while keeping BKT, path generation, cookie auth, and existing tests in place.
- Added deterministic visual-review mock data and fixed the persistent-database API test to compare per-user answer counts by delta.
- Verified the dashboard, graph, practice, repair, path, tracker, analytics, instructor, operations, edge-case, and auth screens in-browser; checked mobile dashboard, graph, path, practice, and responsive table behavior. Added a collapsible navigation breakpoint and corrected mobile graph node clipping found during comparison.
- Checks: frontend type-check passed; frontend tests passed (3); backend tests passed (7); frontend production build passed.


## 2026-09-30 — Security, live data, and adaptive events
- Connected role-aware auth, protected learner/instructor/admin views, logout, refresh rotation, server-side RBAC, user-owned sessions, password validation, configured CORS, security headers, and admin audit entries. Added seeded student, instructor, and admin accounts for local demos.
- Replaced visual mock mode with authenticated backend data for learner analytics, instructor cohort heatmap, admin metrics/flags, misconception evidence, and path revision reasons. Dashboard study time now comes from recorded answer time; admin flags can be reviewed and audited.
- Added authenticated SSE learning events with exponential client reconnect, offline/reconnecting banners, and path update reason toast.
- Added anomaly detection for sub-two-second answers, fast wrong streaks, and repeated-option patterns; suspicious interactions are flagged and down-weighted in BKT. Added confidence reflection, input bounds, rate limits, and an optional strict-JSON misconception provider with retry and rules fallback.
- Removed FastAPI startup event deprecation by moving initialization to lifespan. Test suite output contains no deprecation warnings.
- Verification: TypeScript type-check passed; frontend tests 3 passed; backend tests 16 passed; Vite production build passed. Browser demo verified in the local browser: registered and logged in a learner, submitted a confident wrong answer, observed misconception detection and SSE path reason, then confirmed refreshed analytics and path revision.
