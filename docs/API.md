# API reference

Generated from the FastAPI OpenAPI schema (version `3.1.0`, API `0.2.0`).
Request, response, and parameter schemas are from [openapi.json](openapi.json). The authentication and role notes below come from the same FastAPI route dependencies; protected operations require a valid `access_token` cookie.

## Operations

### `GET /health`

Health

- **Authentication:** Public

**Responses:** `200` Successful Response

### `GET /metrics`

Prometheus Metrics

- **Authentication:** Public

**Responses:** `200` Successful Response

### `POST /api/auth/register`

Register

- **Authentication:** Public

**Request body:** `RegisterIn`

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/auth/login`

Login

- **Authentication:** Public

**Request body:** `RegisterIn`

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/auth/refresh`

Refresh

- **Authentication:** Public

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `refresh_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/auth/me`

Me

- **Authentication:** Required (access_token cookie)

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/auth/logout`

Logout

- **Authentication:** Public

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `refresh_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/courses`

Courses

- **Authentication:** Required (access_token cookie)
- **Role:** student, instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/courses/python-foundations/graph`

Graph

- **Authentication:** Required (access_token cookie)
- **Role:** student, instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/questions/next`

Next Question

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `sessionId` | query | no | object |
| `questionId` | query | no | object |
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/interactions`

Interact

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Request body:** `AnswerIn`

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/learner/state`

Learner State

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/path`

Learning Path

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/misconceptions`

Misconceptions

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `status` | query | no | object |
| `severity` | query | no | object |
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/misconceptions/{misconception_id}/repair`

Misconception Repair

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `misconception_id` | path | yes | integer |
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/analytics`

Analytics

- **Authentication:** Required (access_token cookie)
- **Role:** student

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `period` | query | no | string |
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/instructor/courses`

Instructor Courses

- **Authentication:** Required (access_token cookie)
- **Role:** instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/instructor/courses/{course_id}/enroll`

Enroll Student

- **Authentication:** Required (access_token cookie)
- **Role:** instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `course_id` | path | yes | string |
| `access_token` | cookie | no | object |

**Request body:** `CourseEnrollIn`

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/instructor/overview`

Instructor Overview

- **Authentication:** Required (access_token cookie)
- **Role:** instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/admin/metrics`

Admin Metrics

- **Authentication:** Required (access_token cookie)
- **Role:** admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/admin/flagged`

Flagged Sessions

- **Authentication:** Required (access_token cookie)
- **Role:** admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/admin/evaluation`

Admin Evaluation

- **Authentication:** Required (access_token cookie)
- **Role:** admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

### `POST /api/admin/flagged/{interaction_id}/review`

Review Flag

- **Authentication:** Required (access_token cookie)
- **Role:** admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `interaction_id` | path | yes | integer |
| `access_token` | cookie | no | object |

**Request body:** `FlagReviewIn`

**Responses:** `200` Successful Response; `422` Validation Error

### `GET /api/events`

Events

- **Authentication:** Required (access_token cookie)
- **Role:** student, instructor, admin

| Parameter | In | Required | Schema |
|---|---|---:|---|
| `access_token` | cookie | no | object |

**Responses:** `200` Successful Response; `422` Validation Error

## Schema types

Payload property definitions and exact response schemas are maintained in [openapi.json](openapi.json) under `components.schemas`.
