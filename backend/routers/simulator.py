from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.routers.deps import get_db, require_admin
from backend.models import Device, ScenarioRun, Telemetry
from backend.services import model_store, sim_service
from backend.simulator.profiles import PROFILES
from backend.simulator.scenarios import SCENARIOS

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


class SeedIn(BaseModel):
    hours: int = Field(24, ge=12, le=72)


class TickIn(BaseModel):
    count: int = Field(1, ge=1, le=120)


class ScenarioIn(BaseModel):
    scenario: str
    device_id: str
    duration_ticks: int = Field(20, ge=5, le=120)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    active = db.execute(select(ScenarioRun, Device.device_id).join(Device, Device.id == ScenarioRun.device_pk)
                        .where(ScenarioRun.status == "active")).all()
    return {"devices": db.scalar(select(func.count(Device.id))) or 0,
            "telemetry_rows": db.scalar(select(func.count(Telemetry.id))) or 0,
            "model_ready": model_store.model_ready(db),
            "active_scenarios": [{"scenario": r.scenario, "device_id": d, "ticks_done": r.ticks_done,
                                  "total_ticks": r.total_ticks} for r, d in active]}


@router.get("/devices")
def devices(db: Session = Depends(get_db)):
    return [{"device_id": d.device_id, "device_type": d.device_type, "label": PROFILES[d.device_type].label,
             "facility": d.facility, "is_online": d.is_online}
            for d in db.scalars(select(Device).order_by(Device.id))]


@router.get("/scenarios")
def scenarios():
    return [{"id": k, "description": v} for k, v in SCENARIOS.items()]


@router.post("/seed", dependencies=[Depends(require_admin)])
def seed(body: SeedIn = SeedIn(), db: Session = Depends(get_db)):
    try:
        return sim_service.seed(db, body.hours)
    except sim_service.SimError as e:
        raise HTTPException(400, str(e))


@router.post("/tick", dependencies=[Depends(require_admin)])
def tick(body: TickIn = TickIn(), db: Session = Depends(get_db)):
    try:
        return sim_service.tick(db, body.count)
    except model_store.ModelNotReady as e:
        raise HTTPException(409, str(e))


@router.post("/scenarios", dependencies=[Depends(require_admin)])
def inject(body: ScenarioIn, db: Session = Depends(get_db)):
    try:
        run = sim_service.inject_scenario(db, body.scenario, body.device_id, body.duration_ticks)
    except sim_service.SimError as e:
        raise HTTPException(400, str(e))
    return {"id": run.id, "scenario": run.scenario, "total_ticks": run.total_ticks}
