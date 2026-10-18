from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.routers.deps import get_db, require_admin
from backend.models import Device, Incident

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents(status: str = Query("open", pattern="^(open|resolved|all)$"), db: Session = Depends(get_db)):
    q = select(Incident, Device.device_id).join(Device, Device.id == Incident.device_pk).order_by(Incident.opened_at.desc())
    if status != "all":
        q = q.where(Incident.status == status)
    return [{"id": i.id, "title": i.title, "device_id": dev, "threat_class": i.threat_class, "severity": i.severity,
             "status": i.status, "opened_at": i.opened_at.isoformat(), "last_event_at": i.last_event_at.isoformat(),
             "event_count": i.event_count} for i, dev in db.execute(q.limit(200))]


@router.patch("/{incident_id}/resolve", dependencies=[Depends(require_admin)])
def resolve(incident_id: int, db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, "Incident not found")
    inc.status, inc.resolved_at = "resolved", datetime.now(timezone.utc)
    db.commit()
    return {"id": inc.id, "status": inc.status}
