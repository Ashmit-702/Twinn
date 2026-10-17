import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

from app import models  # noqa: F401  (register tables)
from app.api import dashboard, incidents, simulator
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Device
from app.services import live, sim_service

log = logging.getLogger("twin")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # Milestone 1: no Alembic migrations yet
    if settings.auto_seed:
        with SessionLocal() as s:
            if not s.scalar(select(func.count(Device.id))):
                log.info("AUTO_SEED: %s", sim_service.seed(s))
    if settings.sim_autostart:
        live.start()
    yield
    live.stop()


app = FastAPI(title="TWIN - Smart Factory Security API", version="0.1.0", lifespan=lifespan)

if settings.origins or settings.cors_origin_regex:
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


@app.get("/api/health", tags=["meta"])
def health():
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok", "environment": settings.environment}
