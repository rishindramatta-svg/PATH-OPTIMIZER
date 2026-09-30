# Delivery roadmap by level

Statuses describe what is implemented and what is verified locally as of 2026-10-01. “Fully working” means the repository feature is implemented and covered by available local verification; it does not imply production deployment.

| Level | Fully working | Partial | Not done |
|---|---|---|---|
| **L1 — Product foundation and UI** | Design-token system and all 11 desktop + 4 mobile screen compositions are implemented; shared responsive navigation and edge states are present. | Screen behavior is data-driven, so empty/new accounts differ from the filled references. A fresh final pixel-level browser comparison was not completed in this pass. | New final-stage screenshots for the full demo and a verified pixel-diff report. |
| **L2 — Adaptive learning** | BKT, confidence reflection, misconception detection/repair, adaptive path revision reasons, real analytics, deterministic no-key fallback, and fixed-seed simulator are implemented and tested. | Simulator learning-gain estimates are synthetic; most paired confidence intervals overlap zero and no simulated profile reached the mastery threshold within the fixed budget. | Classroom validation and evidence that the synthetic outcomes generalize to real learners. |
| **L3 — Roles, data, events and abuse handling** | Cookie auth, backend RBAC, per-user data scope, course enrollment/heatmap, admin routes, audit log, authenticated SSE, reconnect behavior, and anomaly heuristics are implemented and locally tested. | Redis-off/process-local mode is single-process only. Heuristic flags can produce false positives or miss varied bots; the optional provider has no guarantee without credentials. | Production-grade multi-worker shared-state and end-to-end security verification. |
| **L4 — Production operation and scale** | PostgreSQL URL/migration support, Redis integration, health/Prometheus metrics, Grafana/Kubernetes/Compose templates, CI workflow, and a reproducible local load-test script exist. | Live PostgreSQL and Docker Compose have not been verified. The measured SQLite load run produced high timeout/error rates and is not production capacity evidence. | A validated live deployment, multi-instance Redis/SSE exercise, and production capacity/SLO results. |

See [evaluation](evaluation.md), [load test](load-test.md), [security notes](security.md), and [visual audit](visual-audit.md).
