"""Lazy, serverless-friendly database access.

Nothing connects at import time, so the app (and the dashboard shell) loads even if DATABASE_URL is
missing; endpoints then answer 503 with a clear message. On Vercel every invocation may run in a fresh
instance, so connections are not pooled in-process (NullPool): use your provider's *pooled* connection
string (PgBouncer / Neon pooler) to keep connection counts low.
"""
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool

from backend.config import get_settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseNotConfigured(RuntimeError):
    pass


_engine: Engine | None = None
_schema_ready = False


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if not url:
            raise DatabaseNotConfigured("DATABASE_URL is not configured on the server.")
        kwargs: dict = {"pool_pre_ping": True}
        if os.getenv("VERCEL"):
            kwargs["poolclass"] = NullPool
        else:
            kwargs.update(pool_size=5, max_overflow=5)
        _engine = create_engine(url, **kwargs)
    return _engine


def SessionLocal() -> Session:  # noqa: N802  (kept as a factory with the familiar name)
    return Session(get_engine(), expire_on_commit=False)


def init_schema_once() -> None:
    """Create tables once per server instance. An advisory lock makes concurrent cold starts safe."""
    global _schema_ready
    if _schema_ready:
        return
    from backend import models  # noqa: F401  (register tables)

    with get_engine().begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(72727401)"))
        Base.metadata.create_all(conn)
    _schema_ready = True


def reset_for_tests() -> None:
    global _engine, _schema_ready
    if _engine is not None:
        _engine.dispose()
    _engine, _schema_ready = None, False
