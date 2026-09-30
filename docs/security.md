# Security notes

## Threat model

| Asset / boundary | Threat | Current control |
|---|---|---|
| Account credentials and sessions | Password disclosure, stolen/stale refresh session | bcrypt hashes; HTTP-only access and refresh cookies; short access lifetime; refresh rotation and revocation; logout endpoint. |
| Learner records | Another student or instructor reads/writes the wrong learner | User-owned reads/writes take the identity from the validated session; route role checks; instructor cohort queries are limited to the instructor's enrolled course. |
| Administrator functions | Unauthorized review or configuration action | Admin-only dependencies and audit records for review actions. |
| Browser/API boundary | Cross-origin credential abuse, framing, MIME sniffing, referrer leakage | Configured CORS allowlist (wildcard rejected with credentials), request-origin check for state-changing API methods, security response headers. |
| Learning signal integrity | Guessing/patterned answers inflate mastery | Fast answers, fast wrong streaks, and repeated-option patterns can be flagged; flagged interactions receive less mastery weight and anomaly events are emitted. Confidence mismatch can prompt reflection. |
| Optional model input | Prompt injection in free-text answers or malformed provider output | Learner text is bounded and treated as data; optional provider requires strict JSON, retries once, then falls back to deterministic rules. The app works without provider credentials. |
| Shared API resources | Brute force or abusive submission volume | Per-user/IP rate limits and input length/range validation. Redis can share limits when configured. |

## Adversarial handling limits

Signals are heuristics. A legitimate quick response can be flagged; a patient or varied bot may evade the rules. Flags are review aids and should not be treated as proof of misconduct. Synthetic guess-detection precision/recall in [evaluation.md](evaluation.md) depends on the simulator labels and is not field validation. The optional LLM path is not required for core learning operations.

## Deployment requirements and known limitations

- Development uses a fallback signing secret and demo credentials (`DemoPass123!`). Never use either in a deployed environment. Production startup rejects known placeholder secrets and requires `COOKIE_SECURE=true`; provide a unique `SECRET_KEY` of at least 32 characters and serve over HTTPS.
- Configure `CORS_ORIGINS` to the actual frontend origins. Do not use wildcard origins with credentials.
- If Redis is absent/unavailable, some cache, rate-limit, and SSE fan-out behavior falls back to in-process state. This is not shared across workers and is unsuitable for horizontally scaled production without Redis.
- The code supports PostgreSQL via `DATABASE_URL`, but a live PostgreSQL service was not available for this verification. SQLite is the verified local database.
- Docker was unavailable for live container/Compose verification; Compose and Kubernetes templates are not evidence of a running deployment.
- HTTPS termination, secret rotation, backups/retention, alerting thresholds, and production incident procedures must be provided by deployment operations.
- See [load-test.md](load-test.md) for the local SQLite 50-VU result and its measured errors. It must not be represented as production capacity.
