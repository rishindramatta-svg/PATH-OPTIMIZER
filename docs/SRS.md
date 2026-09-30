# Software requirements specification

## Purpose and scope

PNG9 is a responsive learning application that estimates per-concept mastery and confidence, detects answer patterns that may indicate misconceptions or guessing, and revises a student's practice sequence. Students use the learning tools; instructors inspect enrolled cohorts; administrators inspect service and model operations.

## Functional requirements

| ID | Requirement | Current implementation |
|---|---|---|
| FR-01 | Register a learner, log in, refresh and revoke cookie sessions, and log out. | Done; seeded demo accounts are also available. |
| FR-02 | Restrict student, instructor, and administrator screens and APIs by role. | Done; backend dependencies enforce route roles. |
| FR-03 | Bind learner state, answers, path, misconceptions, and analytics to the authenticated account. | Done; owner IDs come from the session, not request payloads. |
| FR-04 | Present concept graph, question options, and confidence reflection. | Done. |
| FR-05 | Update mastery with BKT; detect tagged misconception evidence and suspicious answer patterns. | Done. Suspicious attempts are flagged and down-weighted. |
| FR-06 | Show misconception-specific repair examples and follow-up prompts. | Done; deterministic rules are the default, optional strict-JSON provider is supported. |
| FR-07 | Order repairs, due spaced reviews, prerequisite-ready practice, and challenge work; retain revision reason. | Done; revisions are persisted and delivered to the learner. |
| FR-08 | Show analytics with 7-day, 30-day, and all-time periods. | Done; filtering is server-side. |
| FR-09 | Let instructors enroll students and view course-scoped cohort mastery/at-risk data. | Done. |
| FR-10 | Let administrators review flags, service metrics, and synthetic evaluation results. | Done. |
| FR-11 | Publish path, misconception, mastery, and anomaly events and recover after disconnection. | Done with authenticated SSE and client backoff. |
| FR-12 | Show loading, empty, offline, malformed-input, error/retry, quick-answer, and confidence-conflict states. | Implemented; some state layouts remain simpler than the references. |

## Non-functional requirements

- **Security:** bcrypt password hashes; HTTP-only access/refresh cookies and rotation; server-enforced RBAC; configured credentialed CORS; security headers; audit records for administrative actions; bounded inputs; rate limits; prompt-injection-resistant treatment of learner text as data.
- **Privacy:** learner-owned records are scoped by the authenticated user; instructors are scoped to their own courses; administrator routes are separate.
- **Availability:** SQLite supports local development. PostgreSQL is selectable through `DATABASE_URL`; optional Redis accelerates shared cache, event fan-out, and rate state. In-process fallbacks are available when Redis is absent.
- **Performance/scale:** health and Prometheus metrics are exposed. A local SQLite stress result is documented; it is not a production capacity claim.
- **Portability:** Alembic migrations support SQLite and PostgreSQL dialects; Docker/Kubernetes deployment templates are present.
- **Usability:** responsive desktop and mobile layouts, keyboard-operable controls, status/error feedback, and visual references for the 15 supplied compositions.
- **Maintainability:** typed React/TypeScript client, FastAPI/Pydantic API, SQLAlchemy models, migration history, CI checks, and generated OpenAPI/ER references.

## Constraints and assumptions

Learning estimates and simulator results are educational aids, not validated psychometric measurements. The dataset is seeded Python-foundations content. Production deployment must configure strong secrets, HTTPS, allowed origins, and shared backing services. See [security notes](security.md), [evaluation](evaluation.md), and [load test](load-test.md).
