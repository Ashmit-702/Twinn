import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.config import get_settings
from backend.database import get_engine
from backend.routers import dashboard, incidents, simulator
from backend.routers.deps import get_db
from backend.runtime import mode_info

log = logging.getLogger("twin")
settings = get_settings()


class EnsureApiPrefix:
    """Defensive ASGI middleware: all routes live under /api. If the platform hands the function a path
    without that prefix, add it, so the same app works behind any rewrite that strips it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            if path != "/api" and not path.startswith("/api/"):
                scope = dict(scope)
                scope["path"] = "/api" + ("" if path == "/" else path)
                if "raw_path" in scope:
                    scope["raw_path"] = scope["path"].encode()
        await self.app(scope, receive, send)


app = FastAPI(title="TWIN - Smart Factory Security API", version="0.2.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
app.add_middleware(EnsureApiPrefix)

if settings.origins or settings.cors_origin_regex:  # not needed for the same-origin Vercel deployment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )

app.include_router(dashboard.router)
app.include_router(simulator.router)
app.include_router(incidents.router)


@app.get("/api/status", tags=["meta"])
def status(db=Depends(get_db)):
    """Current runtime mode: DEMO MODE or DATABASE CONNECTED (never contains secrets)."""
    return mode_info(db)


@app.get("/api/health", tags=["meta"])
def health():
    """Always 200 when the API itself is up; `mode`/`database` describe the data source."""
    base = {"environment": settings.environment, "admin_key_configured": bool(settings.admin_api_key)}
    if not settings.use_database:
        return {**base, "status": "ok", "mode": "demo", "database": "not configured (demo mode)"}
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        log.exception("health check: database unreachable")
        return {**base, "status": "degraded", "mode": "demo", "database": "unreachable (serving demo data)"}
    return {**base, "status": "ok", "mode": "database", "database": "ok"}
