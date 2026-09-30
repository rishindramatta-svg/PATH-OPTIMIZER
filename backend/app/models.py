from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./png9.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(24), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


Index(
    "ix_course_enrollments_user_course_role",
    CourseEnrollment.user_id,
    CourseEnrollment.course_id,
    CourseEnrollment.role,
    unique=True,
)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Concept(Base):
    __tablename__ = "concepts"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[str] = mapped_column(String(64), index=True, default="python-foundations")
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    concept_slug: Mapped[str] = mapped_column(ForeignKey("concepts.slug"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text, default="")
    misconception_ids: Mapped[list] = mapped_column(JSON, default=list)


class Mastery(Base):
    __tablename__ = "mastery"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept_slug: Mapped[str] = mapped_column(ForeignKey("concepts.slug"), index=True)
    probability: Mapped[float] = mapped_column(Float, default=0.2)
    confidence: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


Index("ix_mastery_user_concept", Mastery.user_id, Mastery.concept_slug, unique=True)


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[int] = mapped_column(Integer)
    time_taken_ms: Mapped[int] = mapped_column(Integer)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str] = mapped_column(String(255), default="")
    session_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="pending")
    mastery_after: Mapped[float] = mapped_column(Float, default=0.2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


Index("ix_interactions_user_created", Interaction.user_id, Interaction.created_at)


class Misconception(Base):
    __tablename__ = "misconceptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept_slug: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="active")
    evidence: Mapped[str] = mapped_column(Text, default="")
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class PathSnapshot(Base):
    __tablename__ = "path_snapshots"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    items: Mapped[list] = mapped_column(JSON, default=list)
    revision: Mapped[dict] = mapped_column(JSON, default=dict)


class PathStep(Base):
    __tablename__ = "path_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    concept_slug: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text, default="")


Index("ix_path_steps_user_position", PathStep.user_id, PathStep.position)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[str] = mapped_column(String(100), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
