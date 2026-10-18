"""DEMO MODE: a synthetic smart factory used whenever PostgreSQL is not configured (or not reachable).

The demo runs the *real* pipeline (simulator -> preprocessing -> Isolation Forest -> IDS -> risk -> incidents)
and stores the result in a throw-away SQLite file in the system temp directory. It is deterministic: the data
depends only on SIM_SEED and a 10-minute time bucket, so every serverless instance generates the same factory
without sharing any state. It is read-only, is NOT persisted, and is regenerated on cold starts, every 10
minutes, and on redeploys.
"""
import logging
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.database import Base

log = logging.getLogger(__name__)
BUCKET_SECONDS = 600
_lock = threading.Lock()
_state: dict = {"bucket": None, "engine": None}


def _build(bucket: int) -> Engine:
    from backend import models  # noqa: F401  (register tables)
    from backend.services import sim_service

    path = Path(tempfile.gettempdir()) / f"twin_demo_{bucket}.db"
    path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    started = time.time()
    with Session(engine, expire_on_commit=False) as session:
        sim_service.seed(session, hours=24, anchor=datetime.fromtimestamp(bucket * BUCKET_SECONDS, tz=timezone.utc),
                         wipe=False)
    log.info("demo data generated in %.1fs", time.time() - started)
    for old in path.parent.glob("twin_demo_*.db"):  # keep the current and previous bucket only
        try:
            if int(old.stem.rsplit("_", 1)[1]) < bucket - 1:
                old.unlink(missing_ok=True)
        except (ValueError, OSError):
            pass
    return engine


def demo_engine() -> Engine:
    bucket = int(time.time() // BUCKET_SECONDS)
    if _state["bucket"] == bucket:
        return _state["engine"]
    with _lock:
        if _state["bucket"] != bucket:
            _state["engine"] = _build(bucket)
            _state["bucket"] = bucket
        return _state["engine"]


def demo_session() -> Session:
    return Session(demo_engine(), expire_on_commit=False)


def reset_for_tests() -> None:
    _state.update(bucket=None, engine=None)
