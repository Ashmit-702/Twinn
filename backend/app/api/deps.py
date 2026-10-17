import hmac

from fastapi import Header, HTTPException

from app.config import get_settings
from app.database import SessionLocal


def get_db():
    with SessionLocal() as session:
        yield session


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Mutating/simulator endpoints. Needs X-Admin-Key when ADMIN_API_KEY is set; refused in production if unset."""
    s = get_settings()
    if s.admin_api_key:
        if not x_admin_key or not hmac.compare_digest(x_admin_key, s.admin_api_key):
            raise HTTPException(401, "Invalid or missing X-Admin-Key")
    elif s.environment == "production":
        raise HTTPException(403, "ADMIN_API_KEY is not configured on the server")
