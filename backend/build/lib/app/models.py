from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./png9.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(24), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

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
