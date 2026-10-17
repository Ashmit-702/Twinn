"""Optional background loop that advances the simulation in real time (single-process)."""
import asyncio
import logging

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.database import SessionLocal
from app.services import model_store, sim_service

log = logging.getLogger(__name__)
_task: asyncio.Task | None = None
_count = 0


def _tick_once() -> None:
    global _count
    with SessionLocal() as session:
        sim_service.tick(session, 1)
        _count += 1
        if _count % 200 == 0:
            sim_service.purge_old_telemetry(session)


async def _loop() -> None:
    while True:
        try:
            await run_in_threadpool(_tick_once)
        except model_store.ModelNotReady:
            pass
        except Exception:
            log.exception("live tick failed")
        await asyncio.sleep(get_settings().sim_tick_seconds)


def start() -> bool:
    global _task
    if running():
        return False
    _task = asyncio.get_running_loop().create_task(_loop())
    return True


def stop() -> bool:
    global _task
    if not running():
        return False
    _task.get_loop().call_soon_threadsafe(_task.cancel)  # may be called from a worker thread
    _task = None
    return True


def running() -> bool:
    return _task is not None and not _task.done()
