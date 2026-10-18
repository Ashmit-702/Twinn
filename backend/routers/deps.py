import hmac
import logging
import time

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend import demo, runtime
from backend.config import get_settings
from backend.database import SessionLocal, init_schema_once

log = logging.getLogger(__name__)
_db_down_until = 0.0  # circuit breaker: after a failure, go straight to demo for a short while
_BREAKER_SECONDS = 30


def get_db():
    """Per-request session.

    PostgreSQL when DATABASE_URL is set and healthy (tables are created and the factory is seeded once,
    idempotently). Otherwise a read-only DEMO session; the reason is exposed through `mode_info`.
    """
    global _db_down_until
    settings = get_settings()
    session: Session | None = None
    reason = "demo_forced" if (settings.force_demo and settings.database_url) else "no_database_configured"

    if settings.use_database and time.time() >= _db_down_until:
        stage = "connect"
        try:
            init_schema_once()
            session = SessionLocal()
            stage = "setup"
            runtime.ensure_seeded(session)
            session.info.update(mode="database", reason=None)
        except Exception:
            log.exception("PostgreSQL %s failed; serving demo data", stage)
            if session is not None:
                session.close()
            session = None
            _db_down_until = time.time() + _BREAKER_SECONDS
            reason = "database_unreachable" if stage == "connect" else "setup_failed"
    elif settings.use_database:
        reason = "database_unreachable"

    if session is None:
        try:
            session = demo.demo_session()
        except Exception:
            log.exception("demo data generation failed")
            raise HTTPException(503, "Demo data could not be generated. Check the function logs.")
        session.info.update(mode="demo", reason=reason)
    try:
        yield session
    finally:
        session.close()


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Endpoints that change data need X-Admin-Key == ADMIN_API_KEY. Refused outright in production if unset."""
    s = get_settings()
    if s.admin_api_key:
        if not x_admin_key or not hmac.compare_digest(x_admin_key, s.admin_api_key):
            raise HTTPException(401, "Invalid or missing admin key")
    elif s.is_production:
        raise HTTPException(403, "ADMIN_API_KEY is not configured on the server")


def require_writes(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)) -> None:
    """Write endpoints: refused in DEMO MODE (nothing would persist), otherwise admin key required."""
    if db.info.get("mode") != "database":
        raise HTTPException(409, "DEMO MODE is read-only. Connect PostgreSQL (set DATABASE_URL) to inject "
                                 "scenarios, advance the simulation or resolve incidents.")
    require_admin(x_admin_key)
