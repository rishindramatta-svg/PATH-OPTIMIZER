# Software requirements summary

## Goal
Help Python learners build mastery through confidence-aware practice, misconception repair and prerequisite-sensitive recommendations.

## Roles and main user stories
- Students register, practice, report confidence and review progress.
- Instructors review class learning signals (planned).
- Administrators review service and audit metrics (planned).

## Quality requirements
Responsive keyboard-accessible UI, validated API payloads, no required LLM secret, explicit suspicious-answer down-weighting, and documented local setup.

## Scope status
Current scaffold delivers local course graph, learner state, practice response, BKT update, confidence gap, suspicious-fast-answer flag and deterministic misconception mapping. Auth hardening, instructor/admin endpoints, WebSockets, analytics, evaluation and deployment-level controls are not implemented yet.
