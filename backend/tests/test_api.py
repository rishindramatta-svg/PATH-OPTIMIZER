import os
from uuid import uuid4

# Ensure Starlette selects the supported test transport rather than legacy httpx.
import httpx2 as _httpx2  # noqa: F401 - preload Starlette's supported test transport

os.environ["DATABASE_URL"] = "sqlite:///./api-tests.db"
from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, Interaction, Question, SessionLocal, User, engine

PASSWORD = "SecurePass123"


def register(client, email=None):
    address = email or f"{uuid4().hex}@example.test"
    response = client.post(
        "/api/auth/register",
        json={"email": address, "password": PASSWORD, "fullName": "Demo Student"},
    )
    assert response.status_code == 200, response.text
    return address, response.json()["user"]


def seeded_login(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": os.getenv("DEMO_PASSWORD", "DemoPass123!")},
    )
    assert response.status_code == 200, response.text
    return response.json()["user"]


def next_question(client):
    response = client.get("/api/questions/next")
    assert response.status_code == 200, response.text
    return response.json()


def test_demo_learning_flow_real_data_and_revision():
    with TestClient(app) as client:
        email, user = register(client)
        assert client.get("/health").json()["status"] == "ok"
        assert len(client.get("/api/courses/python-foundations/graph").json()["concepts"]) == 25
        client.get("/api/path")
        q = next_question(client)
        response = client.post(
            "/api/interactions",
            json={
                "questionId": q["id"],
                "answer": "1",
                "confidence": 5,
                "timeTakenMs": 4000,
                "sessionId": q["sessionId"],
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["correct"] is False
        assert result["misconception"]["status"] == "repairing"
        assert result["misconception"]["evidenceCount"] == 1
        assert result["pathRevision"]["added"] and result["pathRevision"]["removed"]
        assert "confident incorrect answer" in result["pathRevision"]["why"]
        assert client.get("/api/path").json()["revision"]["why"] == result["pathRevision"]["why"]
        assert client.get("/api/learner/state").json()["averageMastery"] > 0
        assert client.get("/api/analytics").json()["questionsAnswered"] == 1
        assert client.get("/api/analytics").json()["masteryTrend"][0]["value"] > 0
        assert len(client.get("/api/misconceptions").json()) == 1
        assert client.get("/api/instructor/overview").status_code == 403
        assert client.get("/api/admin/metrics").status_code == 403
        with TestClient(app) as instructor:
            seeded_login(instructor, "instructor@png9.local")
            assert instructor.get("/api/instructor/overview").json()["activeCount"] >= 1
            assert instructor.get("/api/admin/metrics").status_code == 403
        with TestClient(app) as admin:
            seeded_login(admin, "admin@png9.local")
            metrics = admin.get("/api/admin/metrics").json()
            assert metrics["questions"] == 60 and metrics["interactions"] >= 1
            assert "errorRate" in metrics
            assert admin.get("/api/admin/flagged").status_code == 200
        db = SessionLocal()
        assert db.query(Question).count() == 60
        assert db.query(User).filter_by(email=email).one().role == "student"
        db.close()


def test_auth_refresh_rotation_password_rules_and_logout():
    with TestClient(app) as client:
        email, _ = register(client)
        old_refresh = client.cookies.get("refresh_token")
        assert old_refresh and client.get("/api/auth/me").json()["email"] == email
        assert client.post("/api/auth/refresh").status_code == 200
        rotated = client.cookies.get("refresh_token")
        assert rotated and rotated != old_refresh
        client.cookies.set("refresh_token", old_refresh, path="/api/auth")
        assert client.post("/api/auth/refresh").status_code == 401
        assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
        assert client.post("/api/auth/login", json={"email": email, "password": "WrongPass123"}).status_code == 401
        assert (
            client.post(
                "/api/auth/register",
                json={
                    "email": f"{uuid4().hex}@example.test",
                    "password": "weakpassword",
                },
            ).status_code
            == 422
        )
        assert client.post("/api/auth/logout").json()["ok"] is True
        assert client.get("/api/auth/me").status_code == 401


def test_authentication_rbac_and_client_cannot_choose_data_owner():
    with TestClient(app) as anonymous:
        for url in [
            "/api/courses/python-foundations/graph",
            "/api/questions/next",
            "/api/learner/state",
            "/api/path",
            "/api/misconceptions",
            "/api/analytics",
            "/api/events",
        ]:
            assert anonymous.get(url).status_code == 401
        assert anonymous.get("/api/admin/metrics").status_code == 401
    with TestClient(app) as first, TestClient(app) as second:
        _, first_user = register(first)
        _, second_user = register(second)
        q = next_question(first)
        rejected = first.post(
            "/api/interactions",
            json={
                "questionId": q["id"],
                "answer": "1",
                "confidence": 5,
                "timeTakenMs": 3000,
                "sessionId": q["sessionId"],
                "userId": second_user["id"],
            },
        )
        assert rejected.status_code == 422
        assert (
            first.post(
                "/api/interactions",
                json={
                    "questionId": q["id"],
                    "answer": "1",
                    "confidence": 5,
                    "timeTakenMs": 3000,
                    "sessionId": q["sessionId"],
                },
            ).status_code
            == 200
        )
        assert second.get("/api/learner/state", params={"userId": first_user["id"]}).json()["averageMastery"] == 0
        assert second.get("/api/analytics", params={"userId": first_user["id"]}).json()["questionsAnswered"] == 0
        assert second.get("/api/questions/next", params={"sessionId": q["sessionId"]}).status_code == 404


def test_demo_roles_admin_audit_review_and_cors_security_headers():
    with TestClient(app) as student:
        register(student)
        q = next_question(student)
        flagged = student.post(
            "/api/interactions",
            json={
                "questionId": q["id"],
                "answer": "1",
                "confidence": 2,
                "timeTakenMs": 500,
                "sessionId": q["sessionId"],
            },
        )
        assert flagged.json()["flagged"] is True
        db = SessionLocal()
        flagged_id = db.query(Interaction).order_by(Interaction.id.desc()).first().id
        db.close()
    with TestClient(app) as admin:
        seeded_login(admin, "admin@png9.local")
        flags = admin.get("/api/admin/flagged").json()
        assert any(row["id"] == flagged_id for row in flags)
        interaction_id = flagged_id
        result = admin.post(
            f"/api/admin/flagged/{interaction_id}/review",
            json={"note": "Reviewed suspicious streak"},
        )
        assert result.status_code == 200 and result.json()["status"] == "reviewed"
        db = SessionLocal()
        assert db.query(AuditLog).filter_by(action="admin.flag.reviewed", target_id=str(interaction_id)).count() == 1
        db.close()
    with TestClient(app) as client:
        configured = client.get("/health", headers={"Origin": "http://localhost:5173"})
        blocked = client.get("/health", headers={"Origin": "https://attacker.invalid"})
        assert configured.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert blocked.headers.get("access-control-allow-origin") is None
        for name in [
            "x-content-type-options",
            "x-frame-options",
            "referrer-policy",
            "permissions-policy",
            "content-security-policy",
        ]:
            assert name in configured.headers
        csrf = client.post(
            "/api/auth/register",
            json={"email": f"{uuid4().hex}@example.test", "password": PASSWORD},
            headers={"Origin": "https://attacker.invalid"},
        )
        assert csrf.status_code == 403


def test_role_seeded_accounts_and_restricted_registration_role():
    for address, expected in [
        ("student@png9.local", "student"),
        ("instructor@png9.local", "instructor"),
        ("admin@png9.local", "admin"),
    ]:
        with TestClient(app) as client:
            assert seeded_login(client, address)["role"] == expected
            if expected == "student":
                assert (
                    client.post(
                        "/api/auth/register",
                        json={
                            "email": f"{uuid4().hex}@example.test",
                            "password": PASSWORD,
                            "role": "admin",
                        },
                    ).status_code
                    == 422
                )


def test_analytics_and_misconception_filters_and_evidence_repair():
    with TestClient(app) as client:
        register(client)
        q = next_question(client)
        client.post(
            "/api/interactions",
            json={
                "questionId": q["id"],
                "answer": "1",
                "confidence": 5,
                "timeTakenMs": 4000,
                "sessionId": q["sessionId"],
            },
        ).json()
        assert client.get("/api/analytics?period=7d").json()["questionsAnswered"] == 1
        assert client.get("/api/analytics?period=30d").json()["questionsAnswered"] == 1
        assert client.get("/api/analytics?period=all").json()["questionsAnswered"] == 1
        assert client.get("/api/analytics?period=quarter").status_code == 422
        assert len(client.get("/api/misconceptions?status=repairing&severity=medium").json()) == 1
        assert client.get("/api/misconceptions?status=active").json() == []
        assert client.get("/api/misconceptions?severity=high").json() == []
        misconception = client.get("/api/misconceptions").json()[0]
        example = client.get(f"/api/misconceptions/{misconception['id']}/repair").json()
        assert "Stores 5 in x" in example["counterExample"]
        assert example["followUpQuestion"] and example["options"]
        targeted = client.get("/api/questions/next", params={"questionId": example["questionId"]}).json()
        assert targeted["id"] == example["questionId"]


def test_instructor_scope_and_course_enrollment():
    with TestClient(app) as instructor:
        seeded_login(instructor, "instructor@png9.local")
        email = f"{uuid4().hex}@example.test"
        db = SessionLocal()
        db.add(User(email=email, role="student", hashed_password="test-only"))
        db.commit()
        db.close()
        assert email not in {row["email"] for row in instructor.get("/api/instructor/overview").json()["students"]}
        assert len(instructor.get("/api/instructor/overview").json()["students"]) >= 1
        assert (
            instructor.post(
                "/api/instructor/courses/python-foundations/enroll",
                json={"studentEmail": email},
            ).status_code
            == 200
        )
        names = {row["email"] for row in instructor.get("/api/instructor/overview").json()["students"]}
        assert email in names
        assert instructor.get("/api/instructor/courses").json()[0]["id"] == "python-foundations"
        assert (
            instructor.post("/api/instructor/courses/no-access/enroll", json={"studentEmail": email}).status_code == 403
        )


def test_metrics_request_id_and_db_indexes():
    from sqlalchemy import inspect

    response = TestClient(app).get("/metrics")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    assert "png9_http_request_duration_seconds_bucket" in response.text
    assert "png9_sse_connections_active" in response.text
    indexes = {item["name"] for item in inspect(engine).get_indexes("interactions")}
    assert "ix_interactions_user_created" in indexes
    assert "ix_path_steps_user_position" in {item["name"] for item in inspect(engine).get_indexes("path_steps")}
