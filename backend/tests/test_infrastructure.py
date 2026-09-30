import pytest
from sqlalchemy import create_mock_engine

from app import shared_state
from app.main import validate_production_config
from app.models import Base


def test_postgresql_schema_ddl_compiles_for_server_dialect():
    statements = []
    engine = create_mock_engine(
        "postgresql+psycopg://user:password@localhost/png9",
        lambda sql, *_: statements.append(str(sql.compile(dialect=engine.dialect))),
    )
    Base.metadata.create_all(engine)
    sql = "\n".join(statements)
    assert "CREATE TABLE interactions" in sql
    assert "CREATE TABLE path_steps" in sql
    assert "ix_interactions_user_created" in sql


def test_memory_cache_fallback_and_invalidation(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(shared_state, "redis_client", None)
    shared_state.cache_set("unit:test", {"ok": True}, ttl=30)
    assert shared_state.cache_get("unit:test") == {"ok": True}
    shared_state.cache_delete("unit:test")
    assert shared_state.cache_get("unit:test") is None


def test_production_rejects_placeholder_secret_and_insecure_cookies(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "replace-with-a-generated-64-character-secret")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_config()
    monkeypatch.setenv("SECRET_KEY", "random-local-secret-" + "x" * 40)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        validate_production_config()
    monkeypatch.setenv("COOKIE_SECURE", "true")
    validate_production_config()
