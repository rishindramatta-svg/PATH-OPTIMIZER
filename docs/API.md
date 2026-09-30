# API reference (current)

Interactive OpenAPI: `http://localhost:8000/docs`

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Liveness status |
| GET | `/api/courses` | Course catalog |
| GET | `/api/courses/python-foundations/graph` | Ordered Python concepts and prerequisites |
| POST | `/api/auth/register` | Create local student |
| POST | `/api/auth/login` | Verify credentials and set HTTP-only cookies |
| POST | `/api/auth/refresh` | Refresh the cookie-backed access session |
| GET | `/api/auth/me` | Read the current cookie-backed identity |
| GET | `/api/questions/next` | First seeded practice prompt |
| POST | `/api/interactions` | Score answer and update knowledge state |
| GET | `/api/learner/state` | Concept mastery summary |
| GET | `/api/misconceptions` | Learner misconception list |
| GET | `/api/path` | Prerequisite and repair prioritization |

Interaction request fields: `questionId`, `answer` (option index string), `confidence` (1–5), `timeTakenMs`, optional `userId` (local demo defaults to 1).
