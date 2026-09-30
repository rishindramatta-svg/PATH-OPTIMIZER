from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
from alembic.config import Config
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from alembic import command

from .learning import (
    build_learning_path,
    calibration_label,
    detect_anomalies,
    detect_misconception_id,
    weighted_mastery_update,
)
from .misconception_analysis import configured_analyzer
from .models import (
    AuditLog,
    Concept,
    CourseEnrollment,
    Interaction,
    Mastery,
    Misconception,
    PathSnapshot,
    PathStep,
    PracticeSession,
    Question,
    RefreshSession,
    SessionLocal,
    User,
    engine,
)
from .security import consume_rate_limit
from .seed import seed
from .shared_state import (
    INSTANCE_ID,
    cache_delete,
    cache_get,
    cache_set,
    publish_shared_event,
    start_pubsub,
)


def validate_production_config():
    if os.getenv("ENV", os.getenv("APP_ENV", "development")).lower() == "production":
        secret = os.getenv("SECRET_KEY", "")
        if len(secret) < 32 or secret in {
            "local-development-secret-change-before-deploy",
            "replace-with-a-generated-64-character-secret",
        }:
            raise RuntimeError("Production requires a non-placeholder SECRET_KEY of at least 32 characters")
        if os.getenv("COOKIE_SECURE", "false").lower() != "true":
            raise RuntimeError("COOKIE_SECURE=true is required in production")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_production_config()
    run_migrations()
    seed()
    start_event_fanout()
    yield


app = FastAPI(title="PNG9 Learning Path Optimizer", version="0.2.0", lifespan=lifespan)
app.state.request_count = 0
app.state.server_error_count = 0
JWT_SECRET = os.getenv("SECRET_KEY", "local-development-secret-change-before-deploy")
JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=20)
REFRESH_TTL = timedelta(days=7)
analyzer = configured_analyzer()
logger = logging.getLogger("png9")
request_metrics = {
    "count": 0,
    "errors": 0,
    "latency_sum": 0.0,
    "latency_buckets": defaultdict(int),
    "active_sse": 0,
    "path_latency": [],
    "flagged_sessions": set(),
}


def run_migrations():
    cfg = Config(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url",
        engine.url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    command.upgrade(cfg, "head")


origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
if "*" in origins:
    raise RuntimeError("CORS_ORIGINS cannot contain '*' when credentials are enabled")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Last-Event-ID"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid4())
    origin = request.headers.get("origin")
    if (
        request.method in {"POST", "PATCH", "DELETE"}
        and request.url.path.startswith("/api/")
        and origin
        and origin.rstrip("/") not in origins
    ):
        response = Response(
            content='{"detail":"Origin is not allowed"}',
            status_code=403,
            media_type="application/json",
        )
    else:
        response = await call_next(request)
    elapsed = time.perf_counter() - started
    app.state.request_count += 1
    request_metrics["count"] += 1
    request_metrics["latency_sum"] += elapsed
    request_metrics["latency_buckets"][
        next(
            (bound for bound in (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5) if elapsed <= bound),
            float("inf"),
        )
    ] += 1
    if response.status_code >= 500:
        app.state.server_error_count += 1
        request_metrics["errors"] += 1
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains" if os.getenv("COOKIE_SECURE", "false").lower() == "true" else "max-age=0"
    )
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 3),
            },
            separators=(",", ":"),
        )
    )
    return response


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterIn(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=72)
    fullName: str = Field(default="", max_length=100)


class AnswerIn(StrictModel):
    questionId: int = Field(ge=1)
    answer: str = Field(pattern=r"^[0-9]{1,2}$", max_length=2)
    confidence: int = Field(ge=1, le=5)
    timeTakenMs: int = Field(ge=0, le=3600000)
    sessionId: UUID


class FlagReviewIn(StrictModel):
    note: str = Field(default="Reviewed by administrator", max_length=300)


class CourseEnrollIn(StrictModel):
    studentEmail: str = Field(min_length=3, max_length=254)


def check_rate(key: str, limit: int):
    if not consume_rate_limit(key, limit):
        raise HTTPException(
            429,
            "Too many requests. Please wait before trying again.",
            headers={"Retry-After": "60"},
        )


def validate_email(raw: str) -> str:
    email = raw.strip().lower()
    if any(ord(char) < 32 for char in email) or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
        raise HTTPException(422, "Enter a valid email address")
    return email


def validate_password(password: str):
    if (
        len(password) < 10
        or len(password.encode("utf-8")) > 72
        or not any(c.isupper() for c in password)
        or not any(c.islower() for c in password)
        or not any(c.isdigit() for c in password)
    ):
        raise HTTPException(
            422,
            "Password must have at least 10 characters, an uppercase letter, a lowercase letter and a number",
        )


def set_auth_cookies(response: Response, user: User, db: Session):
    now = datetime.now(UTC)
    access = jwt.encode(
        {"sub": str(user.id), "type": "access", "exp": now + ACCESS_TTL},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    jti = str(uuid4())
    refresh = jwt.encode(
        {"sub": str(user.id), "jti": jti, "type": "refresh", "exp": now + REFRESH_TTL},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    db.add(RefreshSession(jti=jti, user_id=user.id, expires_at=now + REFRESH_TTL))
    db.commit()
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(ACCESS_TTL.total_seconds()),
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(REFRESH_TTL.total_seconds()),
        path="/api/auth",
    )


def public_user(user: User):
    return {"id": user.id, "email": user.email, "role": user.role}


def current_user(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not access_token:
        raise HTTPException(401, "Sign in to continue")
    try:
        claims = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if claims.get("type") != "access":
            raise HTTPException(401, "Invalid access session")
        user = db.get(User, int(claims["sub"]))
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Access session is invalid or expired")
    if not user:
        raise HTTPException(401, "Account no longer exists")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Your account does not have access to this resource")
        return user

    return dependency


Student = Depends(require_roles("student"))
Instructor = Depends(require_roles("instructor", "admin"))
Admin = Depends(require_roles("admin"))
Authenticated = Depends(require_roles("student", "instructor", "admin"))


def require_owned_session(session_id: UUID, user: User, db: Session) -> PracticeSession:
    session = db.get(PracticeSession, str(session_id))
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Practice session not found")
    return session


def build_path(db: Session, user_id: int) -> list[dict]:
    concepts = db.scalars(select(Concept).order_by(Concept.order)).all()
    mastery = {
        m.concept_slug: m.probability for m in db.scalars(select(Mastery).where(Mastery.user_id == user_id)).all()
    }
    active = db.scalars(
        select(Misconception)
        .where(Misconception.user_id == user_id, Misconception.status != "resolved")
        .order_by(desc(Misconception.severity))
    ).all()
    latest_reviews = db.execute(
        select(Question.concept_slug, func.max(Interaction.created_at))
        .join(Interaction, Interaction.question_id == Question.id)
        .where(Interaction.user_id == user_id)
        .group_by(Question.concept_slug)
    ).all()
    now = datetime.now(UTC)
    last_reviewed_days = {
        slug: (
            now - reviewed_at.replace(tzinfo=UTC) if reviewed_at.tzinfo is None else now - reviewed_at
        ).total_seconds()
        / 86400
        for slug, reviewed_at in latest_reviews
    }
    raw = build_learning_path(
        [{"slug": c.slug, "title": c.title, "prerequisites": c.prerequisites} for c in concepts],
        mastery,
        [{"concept_slug": m.concept_slug, "title": m.title, "evidence": m.evidence} for m in active],
        last_reviewed_days,
    )
    observed_times = dict(
        db.execute(
            select(Question.concept_slug, func.avg(Interaction.time_taken_ms))
            .join(Interaction, Interaction.question_id == Question.id)
            .where(Interaction.user_id == user_id)
            .group_by(Question.concept_slug)
        ).all()
    )
    question_counts = dict(
        db.execute(select(Question.concept_slug, func.count(Question.id)).group_by(Question.concept_slug)).all()
    )
    for item in raw:
        observed = observed_times.get(item["conceptId"])
        item["difficulty"] = (
            "Foundation"
            if mastery.get(item["conceptId"], 0.2) < 0.4
            else "Developing"
            if mastery.get(item["conceptId"], 0.2) < 0.75
            else "Advanced"
        )
        item["estimatedMinutes"] = (
            max(1, round(observed * question_counts.get(item["conceptId"], 1) / 60000)) if observed else None
        )
    return raw


def save_path_revision(db: Session, user_id: int, new_items: list[dict], reason: str) -> tuple[dict, bool]:
    snapshot = db.get(PathSnapshot, user_id)
    old_items = snapshot.items if snapshot else []
    old_by = {(x["conceptId"], x["kind"]): x for x in old_items}
    new_by = {(x["conceptId"], x["kind"]): x for x in new_items}
    added = [item for key, item in new_by.items() if key not in old_by]
    removed = [item for key, item in old_by.items() if key not in new_by]
    old_order = [key for key in old_by if key in new_by]
    new_order = [key for key in new_by if key in old_by]
    reordered = []
    if old_order != new_order:
        reordered = [new_by[key] for key in new_order if old_order.index(key) != new_order.index(key)]
    changed = bool(added or removed or reordered)
    revision = {
        "added": added,
        "removed": removed,
        "reordered": reordered,
        "why": reason
        if changed
        else "No sequence change; the current path still matches your latest learning signals.",
    }
    if snapshot and changed:
        snapshot.items, snapshot.revision = new_items, revision
    elif snapshot:
        revision = snapshot.revision
    else:
        db.add(PathSnapshot(user_id=user_id, items=new_items, revision=revision))
    db.query(PathStep).filter(PathStep.user_id == user_id).delete(synchronize_session=False)
    db.add_all(
        [
            PathStep(
                user_id=user_id,
                position=index,
                concept_slug=item["conceptId"],
                kind=item["kind"],
                reason=item["reason"],
            )
            for index, item in enumerate(new_items)
        ]
    )
    return revision, changed


class EventBroker:
    def __init__(self):
        self.subscribers: dict[int, set[asyncio.Queue]] = {}

    def subscribe(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        self.subscribers.setdefault(user_id, set()).add(queue)
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue):
        self.subscribers.get(user_id, set()).discard(queue)

    async def publish(self, user_id: int, event: str, data: dict):
        publish_shared_event(user_id, event, data)
        await self.publish_local(user_id, event, data)

    async def publish_local(self, user_id: int, event: str, data: dict):
        for queue in tuple(self.subscribers.get(user_id, set())):
            try:
                queue.put_nowait({"event": event, "data": data})
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                queue.put_nowait({"event": event, "data": data})


event_broker = EventBroker()
_event_loop = None


def start_event_fanout():
    global _event_loop
    _event_loop = asyncio.get_running_loop()

    def dispatch(item):
        if item.get("origin") == INSTANCE_ID:
            return
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                event_broker.publish_local(item["userId"], item["event"], item["data"]),
                _event_loop,
            )

    start_pubsub(dispatch)


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(select(1))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        logger.error(json.dumps({"event": "health_database_failure", "reason": str(exc)}))
        raise HTTPException(503, "Database unavailable")


@app.get("/metrics", response_class=Response)
def prometheus_metrics():
    lines = [
        "# HELP png9_http_requests_total Total HTTP requests",
        "# TYPE png9_http_requests_total counter",
        f"png9_http_requests_total {request_metrics['count']}",
        "# HELP png9_http_errors_total Total HTTP 5xx responses",
        "# TYPE png9_http_errors_total counter",
        f"png9_http_errors_total {request_metrics['errors']}",
        "# HELP png9_http_request_duration_seconds_sum Request duration sum",
        "# TYPE png9_http_request_duration_seconds_sum counter",
        f"png9_http_request_duration_seconds_sum {request_metrics['latency_sum']:.6f}",
        "# HELP png9_sse_connections_active Current open SSE connections",
        "# TYPE png9_sse_connections_active gauge",
        f"png9_sse_connections_active {request_metrics['active_sse']}",
        "# HELP png9_path_update_duration_ms Path optimizer latency",
        "# TYPE png9_path_update_duration_ms summary",
        f"png9_flagged_interactions_total {request_metrics.get('flagged_total', 0)}",
        "# HELP png9_flagged_interactions_total Flagged learner interactions",
        "# TYPE png9_flagged_interactions_total counter",
        "# HELP png9_flagged_sessions_active Unique flagged practice sessions observed by this process",
        "# TYPE png9_flagged_sessions_active gauge",
        f"png9_flagged_sessions_active {len(request_metrics['flagged_sessions'])}",
        "# HELP png9_http_request_duration_seconds Histogram of request latency",
        "# TYPE png9_http_request_duration_seconds histogram",
    ]
    for bound in (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, float("inf")):
        count = sum(v for key, v in request_metrics["latency_buckets"].items() if key <= bound)
        label = "+Inf" if bound == float("inf") else str(bound)
        lines.append(f'png9_http_request_duration_seconds_bucket{{le="{label}"}} {count}')
    lines.extend(
        [
            f"png9_http_request_duration_seconds_count {request_metrics['count']}",
            f"png9_http_request_duration_seconds_sum {request_metrics['latency_sum']:.6f}",
        ]
    )
    observations = request_metrics["path_latency"]
    if observations:
        lines += [
            f'png9_path_update_duration_ms{{quantile="0.5"}} {_percentile_runtime(observations, 0.5)}',
            f'png9_path_update_duration_ms{{quantile="0.95"}} {_percentile_runtime(observations, 0.95)}',
        ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


def _percentile_runtime(values, q):
    return round(sorted(values)[min(len(values) - 1, int((len(values) - 1) * q))], 3)


@app.post("/api/auth/register")
def register(
    body: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    check_rate(f"auth:{request.client.host if request.client else 'unknown'}", 10)
    email = validate_email(body.email)
    validate_password(body.password)
    if any(ord(char) < 32 for char in body.fullName):
        raise HTTPException(422, "Name contains invalid characters")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(
        email=email,
        hashed_password=bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_auth_cookies(response, user, db)
    return {"user": public_user(user)}


@app.post("/api/auth/login")
def login(
    body: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = validate_email(body.email)
    check_rate(f"login:{request.client.host if request.client else 'unknown'}:{email}", 10)
    user = db.scalar(select(User).where(User.email == email))
    if (
        not user
        or not user.hashed_password
        or not bcrypt.checkpw(body.password.encode(), user.hashed_password.encode())
    ):
        raise HTTPException(401, "Email or password is incorrect")
    set_auth_cookies(response, user, db)
    return {"user": public_user(user)}


@app.post("/api/auth/refresh")
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(401, "Refresh session is missing")
    try:
        claims = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if claims.get("type") != "refresh":
            raise HTTPException(401, "Invalid refresh session")
        record = db.get(RefreshSession, claims["jti"])
        if not record or record.revoked_at or record.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
            raise HTTPException(401, "Refresh session is revoked or expired")
        user = db.get(User, int(claims["sub"]))
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Refresh session is invalid or expired")
    if not user or record.user_id != user.id:
        raise HTTPException(401, "Account no longer exists")
    record.revoked_at = datetime.now(UTC)
    db.commit()
    set_auth_cookies(response, user, db)
    return {"user": public_user(user)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


@app.post("/api/auth/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if refresh_token:
        try:
            claims = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            record = db.get(RefreshSession, claims.get("jti"))
            if record and not record.revoked_at:
                record.revoked_at = datetime.now(UTC)
                db.commit()
        except (JWTError, TypeError):
            pass
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}


@app.get("/api/courses")
def courses(db: Session = Depends(get_db), user: User = Authenticated):
    return [
        {
            "id": "python-foundations",
            "title": "Python Programming",
            "conceptCount": db.query(Concept).count(),
        }
    ]


@app.get("/api/courses/python-foundations/graph")
def graph(db: Session = Depends(get_db), user: User = Authenticated):
    cached = cache_get("graph:python-foundations")
    if cached is not None:
        return {"concepts": cached}
    concepts = db.scalars(select(Concept).order_by(Concept.order)).all()
    result = [
        {
            "id": c.slug,
            "title": c.title,
            "description": c.description,
            "prerequisites": c.prerequisites,
            "order": c.order,
        }
        for c in concepts
    ]
    cache_set("graph:python-foundations", result, 600)
    return {"concepts": result}


@app.get("/api/questions/next")
def next_question(
    sessionId: UUID | None = None,
    questionId: int | None = None,
    db: Session = Depends(get_db),
    user: User = Student,
):
    if sessionId:
        session = require_owned_session(sessionId, user, db)
    else:
        session = PracticeSession(id=str(uuid4()), user_id=user.id)
        db.add(session)
        db.commit()
    q = db.get(Question, questionId) if questionId else db.scalar(select(Question).order_by(Question.id).limit(1))
    if not q:
        raise HTTPException(404, "Question not found")
    return {
        "id": q.id,
        "conceptId": q.concept_slug,
        "prompt": q.prompt,
        "options": q.options,
        "sessionId": session.id,
    }


@app.post("/api/interactions")
async def interact(body: AnswerIn, db: Session = Depends(get_db), user: User = Student):
    check_rate(f"interaction:{user.id}", 60)
    request_metrics["flagged_total"] = request_metrics.get("flagged_total", 0)
    practice_session = require_owned_session(body.sessionId, user, db)
    question = db.get(Question, body.questionId)
    if not question:
        raise HTTPException(404, "Question not found")
    selected = int(body.answer)
    if selected not in range(len(question.options)):
        raise HTTPException(422, "Answer option is out of range")
    correct = selected == question.correct_index
    recent_rows = db.scalars(
        select(Interaction)
        .where(
            Interaction.user_id == user.id,
            Interaction.session_id == str(body.sessionId),
        )
        .order_by(desc(Interaction.created_at))
        .limit(4)
    ).all()
    recent = [
        {"answer": row.answer, "correct": row.correct, "confidence": row.confidence} for row in reversed(recent_rows)
    ]
    anomaly_reasons = detect_anomalies(body.timeTakenMs, correct, body.answer, body.confidence, recent)
    flagged = bool(anomaly_reasons)
    if flagged:
        request_metrics["flagged_total"] += 1
        request_metrics["flagged_sessions"].add(str(body.sessionId))
    mastery = db.scalar(
        select(Mastery).where(Mastery.user_id == user.id, Mastery.concept_slug == question.concept_slug)
    )
    if not mastery:
        mastery = Mastery(user_id=user.id, concept_slug=question.concept_slug, probability=0.2)
        db.add(mastery)
        db.flush()
    mastery.probability = weighted_mastery_update(mastery.probability, correct, anomaly_reasons)
    mastery.confidence = body.confidence
    interaction = Interaction(
        user_id=user.id,
        question_id=question.id,
        answer=body.answer,
        correct=correct,
        confidence=body.confidence,
        time_taken_ms=body.timeTakenMs,
        flagged=flagged,
        anomaly_reason=",".join(anomaly_reasons),
        session_id=str(body.sessionId),
        mastery_after=mastery.probability,
    )
    db.add(interaction)
    if flagged:
        practice_session.anomaly_count += 1

    found = None
    newly_detected = False
    analysis = None
    misconception_key = detect_misconception_id({"misconception_ids": question.misconception_ids}, selected)
    if not correct and misconception_key:
        key = misconception_key
        analysis = analyzer.analyze(
            key,
            question.options[question.correct_index],
            question.explanation,
            question.options[selected],
        )
        found = db.scalar(select(Misconception).where(Misconception.user_id == user.id, Misconception.key == key))
        if not found:
            newly_detected = True
            found = Misconception(
                user_id=user.id,
                concept_slug=question.concept_slug,
                key=key,
                title=analysis.title,
                severity=0,
                evidence=analysis.explanation,
                evidence_count=1,
            )
            db.add(found)
        else:
            found.evidence_count += 1
        found.title = analysis.title
        found.evidence = analysis.explanation
        found.last_seen_at = datetime.now(UTC)
        found.severity = min(5, max(found.severity + 1 + (body.confidence >= 4), analysis.severity))
        found.status = "repairing" if body.confidence >= 4 else "active"

    db.flush()
    reason = (
        "A confident incorrect answer triggered a targeted repair and moved it ahead of the next practice topic."
        if found and body.confidence >= 4
        else "A misconception was detected; the path now puts its repair before new topics."
        if found
        else "Suspicious response patterns were down-weighted while the path was recalculated."
        if flagged
        else "The next step reflects your latest mastery update."
    )
    path_started = time.perf_counter()
    new_path = build_path(db, user.id)
    request_metrics["path_latency"].append(round((time.perf_counter() - path_started) * 1000, 3))
    if len(request_metrics["path_latency"]) > 1000:
        del request_metrics["path_latency"][:500]
    revision, path_changed = save_path_revision(db, user.id, new_path, reason)
    db.commit()
    cache_delete(f"path:{user.id}")

    result = {
        "correct": correct,
        "mastery": mastery.probability,
        "calibrationGap": body.confidence / 5 - mastery.probability,
        "calibrationLabel": calibration_label(body.confidence, mastery.probability),
        "flagged": flagged,
        "anomalyReasons": anomaly_reasons,
        "misconception": (
            {
                "title": found.title,
                "severity": found.severity,
                "status": found.status,
                "explanation": analysis.explanation,
                "evidenceCount": found.evidence_count,
            }
            if found
            else None
        ),
        "path": new_path,
        "pathRevision": revision,
        "feedback": analysis.explanation if analysis else question.explanation,
    }
    await event_broker.publish(
        user.id,
        "mastery_updated",
        {"conceptId": question.concept_slug, "mastery": mastery.probability},
    )
    if found and newly_detected:
        await event_broker.publish(
            user.id,
            "misconception_detected",
            {"title": found.title, "reason": analysis.explanation},
        )
    if flagged:
        await event_broker.publish(
            user.id,
            "anomaly_flagged",
            {"reasons": anomaly_reasons, "sessionId": str(body.sessionId)},
        )
    if path_changed:
        await event_broker.publish(user.id, "path_updated", {"reason": revision["why"], "revision": revision})
    return result


@app.get("/api/learner/state")
def learner_state(db: Session = Depends(get_db), user: User = Student):
    concepts = db.scalars(select(Concept).order_by(Concept.order)).all()
    mastery = {
        m.concept_slug: m.probability for m in db.scalars(select(Mastery).where(Mastery.user_id == user.id)).all()
    }
    attempts = db.scalars(select(Interaction).where(Interaction.user_id == user.id)).all()
    streak = min(len(attempts), 30)
    return {
        "mastery": [
            {
                "conceptId": c.slug,
                "title": c.title,
                "probability": mastery.get(c.slug, 0.2),
            }
            for c in concepts
        ],
        "averageMastery": sum(mastery.values()) / len(mastery) if mastery else 0,
        "streak": streak,
    }


@app.get("/api/path")
def learning_path(db: Session = Depends(get_db), user: User = Student):
    cached = cache_get(f"path:{user.id}")
    if cached is not None:
        return cached
    items = build_path(db, user.id)
    snapshot = db.get(PathSnapshot, user.id)
    if not snapshot:
        revision = {
            "added": items[:1],
            "removed": [],
            "reordered": [],
            "why": "Your initial path is based on prerequisite order and current mastery.",
        }
        db.add(PathSnapshot(user_id=user.id, items=items, revision=revision))
        db.commit()
        db.add_all(
            [
                PathStep(
                    user_id=user.id,
                    position=i,
                    concept_slug=item["conceptId"],
                    kind=item["kind"],
                    reason=item["reason"],
                )
                for i, item in enumerate(items)
            ]
        )
        db.commit()
    else:
        before = snapshot.items
        revision, changed = save_path_revision(
            db,
            user.id,
            items,
            "The path was reconciled with your latest mastery and misconception evidence.",
        )
        if changed or before != items:
            db.commit()
    snapshot = db.get(PathSnapshot, user.id)
    result = {"items": items, "revision": snapshot.revision}
    cache_set(f"path:{user.id}", result, 120)
    return result


@app.get("/api/misconceptions")
def misconceptions(
    status: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
    user: User = Student,
):
    query = select(Misconception).where(Misconception.user_id == user.id)
    if status:
        if status not in {"active", "repairing", "resolved"}:
            raise HTTPException(422, "Invalid misconception status")
        query = query.where(Misconception.status == status)
    if severity:
        severity_bounds = {"low": (0, 1), "medium": (2, 3), "high": (4, 5)}
        if severity not in severity_bounds:
            raise HTTPException(422, "Severity must be low, medium, or high")
        low, high = severity_bounds[severity]
        query = query.where(Misconception.severity >= low, Misconception.severity <= high)
    rows = db.scalars(query.order_by(desc(Misconception.last_seen_at))).all()
    return [
        {
            "id": m.id,
            "conceptId": m.concept_slug,
            "title": m.title,
            "severity": m.severity,
            "status": m.status,
            "evidence": m.evidence,
            "evidenceCount": m.evidence_count,
            "lastSeenAt": m.last_seen_at.isoformat(),
        }
        for m in rows
    ]


@app.get("/api/misconceptions/{misconception_id}/repair")
def misconception_repair(misconception_id: int, db: Session = Depends(get_db), user: User = Student):
    item = db.scalar(
        select(Misconception).where(Misconception.id == misconception_id, Misconception.user_id == user.id)
    )
    if not item:
        raise HTTPException(404, "Misconception not found")
    questions = db.scalars(
        select(Question).where(Question.concept_slug == item.concept_slug).order_by(Question.id)
    ).all()
    tagged = next((q for q in questions if item.key in (q.misconception_ids or [])), None)
    if not tagged:
        raise HTTPException(404, "No authored repair evidence found for this misconception")
    wrong_index = (tagged.misconception_ids or []).index(item.key)
    correct = tagged.options[tagged.correct_index]
    misconception_choice = tagged.options[wrong_index]
    follow_up = next((q for q in questions if q.id != tagged.id), tagged)
    return {
        "misconceptionId": item.id,
        "counterExample": f"For “{tagged.prompt}”, “{misconception_choice}” is the misconception pattern. The counter-example is “{correct}”: it {tagged.explanation.lower()}",
        "followUpQuestion": follow_up.prompt,
        "options": follow_up.options,
        "questionId": follow_up.id,
    }


@app.get("/api/analytics")
def analytics(period: str = "all", db: Session = Depends(get_db), user: User = Student):
    if period not in {"7d", "30d", "all"}:
        raise HTTPException(422, "Period must be 7d, 30d, or all")
    query = select(Interaction).where(Interaction.user_id == user.id)
    if period != "all":
        query = query.where(Interaction.created_at >= datetime.now(UTC) - timedelta(days=int(period[:-1])))
    attempts = db.scalars(query.order_by(Interaction.created_at)).all()
    concepts = db.scalars(select(Concept).order_by(Concept.order)).all()
    mastery = {
        m.concept_slug: m.probability for m in db.scalars(select(Mastery).where(Mastery.user_id == user.id)).all()
    }
    total = len(attempts)
    correct = sum(1 for a in attempts if a.correct)
    by_concept = []
    for concept in concepts:
        items = [a for a in attempts if db.get(Question, a.question_id).concept_slug == concept.slug]
        by_concept.append(
            {
                "conceptId": concept.slug,
                "title": concept.title,
                "mastery": mastery.get(concept.slug, 0.2),
                "attempts": len(items),
                "accuracy": sum(1 for a in items if a.correct) / len(items) if items else 0,
            }
        )
    windows = [attempts[max(0, i - 4) : i + 1] for i in range(0, len(attempts), 5)]
    trend = [
        {
            "label": f"Set {i + 1}",
            "value": sum(a.mastery_after for a in group) / len(group),
        }
        for i, group in enumerate(windows[-6:])
    ]
    return {
        "questionsAnswered": total,
        "accuracy": correct / total if total else 0,
        "averageConfidence": sum(a.confidence for a in attempts) / total / 5 if total else 0,
        "guessRate": sum(1 for a in attempts if a.correct and a.confidence <= 2) / max(1, correct),
        "flagged": sum(1 for a in attempts if a.flagged),
        "studyMinutes": sum(a.time_taken_ms for a in attempts) / 60000,
        "masteryTrend": trend,
        "concepts": by_concept,
    }


@app.get("/api/instructor/courses")
def instructor_courses(db: Session = Depends(get_db), user: User = Instructor):
    if user.role == "admin":
        course_ids = [
            row[0]
            for row in db.execute(
                select(CourseEnrollment.course_id).where(CourseEnrollment.role == "instructor").distinct()
            ).all()
        ]
    else:
        course_ids = [
            row[0]
            for row in db.execute(
                select(CourseEnrollment.course_id).where(
                    CourseEnrollment.user_id == user.id,
                    CourseEnrollment.role == "instructor",
                )
            ).all()
        ]
    return [
        {
            "id": course_id,
            "title": "Python Foundations",
            "studentCount": db.scalar(
                select(func.count())
                .select_from(CourseEnrollment)
                .where(
                    CourseEnrollment.course_id == course_id,
                    CourseEnrollment.role == "student",
                )
            )
            or 0,
        }
        for course_id in course_ids
    ]


@app.post("/api/instructor/courses/{course_id}/enroll")
def enroll_student(
    course_id: str,
    body: CourseEnrollIn,
    db: Session = Depends(get_db),
    user: User = Instructor,
):
    owns_course = db.scalar(
        select(CourseEnrollment.id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user.id,
            CourseEnrollment.role == "instructor",
        )
    )
    if user.role != "admin" and not owns_course:
        raise HTTPException(403, "You are not assigned to this course")
    email = validate_email(body.studentEmail)
    student = db.scalar(select(User).where(User.email == email, User.role == "student"))
    if not student:
        raise HTTPException(404, "Student account not found")
    row = db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == student.id,
            CourseEnrollment.role == "student",
        )
    )
    if not row:
        db.add(
            CourseEnrollment(
                course_id=course_id,
                user_id=student.id,
                role="student",
                instructor_id=user.id,
            )
        )
        db.commit()
    return {"ok": True, "courseId": course_id, "studentId": student.id}


@app.get("/api/instructor/overview")
def instructor_overview(db: Session = Depends(get_db), user: User = Instructor):
    if user.role == "admin":
        course_ids = [
            row[0]
            for row in db.execute(
                select(CourseEnrollment.course_id).where(CourseEnrollment.role == "instructor").distinct()
            ).all()
        ]
        users = (
            db.scalars(
                select(User)
                .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
                .where(
                    User.role == "student",
                    CourseEnrollment.course_id.in_(course_ids) if course_ids else False,
                )
                .order_by(User.id)
                .limit(128)
            )
            .unique()
            .all()
            if course_ids
            else []
        )
    else:
        course_ids = [
            row[0]
            for row in db.execute(
                select(CourseEnrollment.course_id).where(
                    CourseEnrollment.user_id == user.id,
                    CourseEnrollment.role == "instructor",
                )
            ).all()
        ]
        users = (
            db.scalars(
                select(User)
                .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
                .where(
                    User.role == "student",
                    CourseEnrollment.course_id.in_(course_ids),
                    CourseEnrollment.instructor_id == user.id,
                )
                .order_by(User.id)
                .limit(128)
            )
            .unique()
            .all()
            if course_ids
            else []
        )
    concepts = db.scalars(select(Concept).order_by(Concept.order).limit(9)).all()
    student_rows = []
    for student in users:
        mastery = {
            m.concept_slug: m.probability
            for m in db.scalars(select(Mastery).where(Mastery.user_id == student.id)).all()
        }
        attempts = db.scalars(select(Interaction).where(Interaction.user_id == student.id)).all()
        mis = db.scalars(
            select(Misconception).where(Misconception.user_id == student.id, Misconception.status != "resolved")
        ).all()
        values = [mastery.get(c.slug, 0.2) for c in concepts]
        student_rows.append(
            {
                "id": student.id,
                "name": student.email.split("@")[0],
                "email": student.email,
                "mastery": values,
                "average": sum(values) / len(values) if values else 0,
                "flagged": sum(1 for a in attempts if a.flagged),
                "misconceptions": len(mis),
            }
        )
    return {
        "students": student_rows,
        "concepts": [{"id": c.slug, "title": c.title} for c in concepts],
        "activeCount": len(users),
        "averageMastery": sum(s["average"] for s in student_rows) / len(student_rows) if student_rows else 0,
        "flaggedStudents": sum(1 for s in student_rows if s["flagged"]),
        "misconceptionClusters": sum(1 for s in student_rows if s["misconceptions"]),
    }


def audit(
    db: Session,
    actor: User,
    action: str,
    target_id: str = "",
    details: dict | None = None,
):
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action=action,
            target_id=target_id,
            details=details or {},
        )
    )
    db.commit()


@app.get("/api/admin/metrics")
def admin_metrics(db: Session = Depends(get_db), user: User = Admin):
    metrics = {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "concepts": db.scalar(select(func.count()).select_from(Concept)) or 0,
        "questions": db.scalar(select(func.count()).select_from(Question)) or 0,
        "interactions": db.scalar(select(func.count()).select_from(Interaction)) or 0,
        "flagged": db.scalar(select(func.count()).select_from(Interaction).where(Interaction.flagged.is_(True))) or 0,
        "activeMisconceptions": db.scalar(
            select(func.count()).select_from(Misconception).where(Misconception.status != "resolved")
        )
        or 0,
    }
    metrics["errorRate"] = app.state.server_error_count / max(1, app.state.request_count)
    audit(db, user, "admin.metrics.viewed")
    return metrics


@app.get("/api/admin/flagged")
def flagged_sessions(db: Session = Depends(get_db), user: User = Admin):
    rows = db.scalars(
        select(Interaction).where(Interaction.flagged.is_(True)).order_by(desc(Interaction.created_at)).limit(100)
    ).all()
    audit(db, user, "admin.flagged.viewed")
    return [
        {
            "id": row.id,
            "studentId": row.user_id,
            "createdAt": row.created_at.isoformat(),
            "confidence": row.confidence / 5,
            "reason": row.anomaly_reason or "Suspicious response pattern",
            "status": row.review_status,
        }
        for row in rows
    ]


@app.get("/api/admin/evaluation")
def admin_evaluation(user: User = Admin):
    from .evaluation.simulator import simulate

    return simulate()


@app.post("/api/admin/flagged/{interaction_id}/review")
def review_flag(
    interaction_id: int,
    body: FlagReviewIn,
    db: Session = Depends(get_db),
    user: User = Admin,
):
    if any(ord(char) < 32 for char in body.note):
        raise HTTPException(422, "Review note contains invalid characters")
    row = db.get(Interaction, interaction_id)
    if not row or not row.flagged:
        raise HTTPException(404, "Flagged interaction not found")
    row.review_status = "reviewed"
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="admin.flag.reviewed",
            target_id=str(interaction_id),
            details={"note": body.note[:300]},
        )
    )
    db.commit()
    return {"ok": True, "status": row.review_status}


@app.get("/api/events")
async def events(user: User = Authenticated):
    queue = event_broker.subscribe(user.id)
    request_metrics["active_sse"] += 1

    async def stream():
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {item['event']}\ndata: {json.dumps(item['data'], separators=(',', ':'))}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            request_metrics["active_sse"] = max(0, request_metrics["active_sse"] - 1)
            event_broker.unsubscribe(user.id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
