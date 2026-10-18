from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.routers.deps import get_db
from backend.services import dashboard as svc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return svc.summary(db)


@router.get("/twins")
def twins(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return svc.twins(db, limit)


@router.get("/events")
def events(limit: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    return svc.events(db, limit)


@router.get("/threats-timeline")
def timeline(hours: int = Query(24, ge=1, le=72), db: Session = Depends(get_db)):
    return svc.threats_timeline(db, hours)


@router.get("/anomaly-distribution")
def distribution(db: Session = Depends(get_db)):
    return svc.anomaly_distribution(db)


@router.get("/device-status")
def device_status(db: Session = Depends(get_db)):
    return svc.device_status(db)


@router.get("/overview")
def overview(hours: int = Query(24, ge=1, le=72), db: Session = Depends(get_db)):
    """Everything the dashboard needs in one request (one serverless invocation instead of six)."""
    return {"summary": svc.summary(db), "twins": svc.twins(db, 100), "events": svc.events(db, 50),
            "timeline": svc.threats_timeline(db, hours), "distribution": svc.anomaly_distribution(db),
            "device_status": svc.device_status(db)}
