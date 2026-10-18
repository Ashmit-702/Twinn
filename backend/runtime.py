"""Runtime mode (DEMO vs DATABASE) and idempotent first-run database setup."""
import threading

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Device

_seed_lock = threading.Lock()
_seed_checked = False

_DEMO_TEXT = {
    "no_database_configured": "No database is configured, so TWIN is running on synthetic demo data.",
    "demo_forced": "DEMO_MODE is enabled, so TWIN is running on synthetic demo data.",
    "database_unreachable": "DATABASE_URL is set but the database could not be reached, so TWIN fell back to demo data.",
    "setup_failed": "The database is reachable but automatic setup failed, so TWIN fell back to demo data.",
}


def mode_info(session: Session) -> dict:
    mode = session.info.get("mode", "demo")
    reason = session.info.get("reason")
    if mode == "database":
        message = "Connected to PostgreSQL. Data is persistent."
    else:
        message = (_DEMO_TEXT.get(reason, _DEMO_TEXT["no_database_configured"])
                   + " Demo data is generated on the server and is read-only. It is not saved: it can differ "
                     "between serverless requests/instances and is regenerated on redeploys. Set DATABASE_URL "
                     "to enable persistent PostgreSQL storage.")
    return {"mode": mode, "label": "DATABASE CONNECTED" if mode == "database" else "DEMO MODE",
            "database_connected": mode == "database", "persistent": mode == "database",
            "writes_enabled": mode == "database", "reason": reason,
            "admin_key_configured": bool(get_settings().admin_api_key), "message": message}


def ensure_seeded(session: Session) -> None:
    """Seed the factory (devices, twins, 24 h of telemetry, model) exactly once, only if the database is empty.

    Safe under concurrency: a PostgreSQL advisory lock serialises instances and the emptiness check is repeated
    inside the lock; unique constraints on device ids and twin codes are a second guard. After the first check
    per instance this costs nothing.
    """
    global _seed_checked
    if _seed_checked:
        return
    with _seed_lock:
        if _seed_checked:
            return
        if not session.scalar(select(func.count(Device.id))):
            session.execute(text("SELECT pg_advisory_xact_lock(72727402)"))
            if not session.scalar(select(func.count(Device.id))):  # re-check: another instance may have seeded
                from backend.services import sim_service
                sim_service.seed(session, wipe=False)  # commits (releases the lock)
            else:
                session.commit()
        _seed_checked = True


def reset_for_tests() -> None:
    global _seed_checked
    _seed_checked = False
