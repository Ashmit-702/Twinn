import hmac
import logging

from fastapi import Header, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.database import DatabaseNotConfigured, SessionLocal, init_schema_once

log = logging.getLogger(__name__)


def get_db():
    """Per-request session. Misconfiguration/outages become clean 503s that never leak connection details."""
    try:
        init_schema_once()
        session = SessionLocal()
    except DatabaseNotConfigured as e:
        raise HTTPException(503, str(e))
    except SQLAlchemyError:
        log.exception("database connection/schema initialisation failed")
        raise HTTPException(503, "Cannot connect to the database. Check DATABASE_URL and that the database is reachable.")
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
