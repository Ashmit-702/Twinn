from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Device, DigitalTwin, SecurityEvent, Telemetry


def refresh_twins(session: Session, now: datetime, window_minutes: int) -> None:
    """security_score = 100 - max(0.6 * max recent event risk, 0.1 * latest anomaly score)."""
    since = now - timedelta(minutes=window_minutes)
    last_ts = select(Telemetry.device_pk, func.max(Telemetry.ts).label("ts")).group_by(Telemetry.device_pk).subquery()
    latest = dict(session.execute(
        select(Telemetry.device_pk, Telemetry.anomaly_score)
        .join(last_ts, (Telemetry.device_pk == last_ts.c.device_pk) & (Telemetry.ts == last_ts.c.ts))).all())
    risk = dict(session.execute(
        select(SecurityEvent.device_pk, func.max(SecurityEvent.risk_score))
        .where(SecurityEvent.ts >= since).group_by(SecurityEvent.device_pk)).all())
    online = dict(session.execute(select(Device.id, Device.is_online)).all())
    for twin in session.scalars(select(DigitalTwin)):
        score = 100 - max(0.6 * (risk.get(twin.device_pk) or 0), 0.1 * (latest.get(twin.device_pk) or 0))
        twin.security_score = round(max(0.0, min(100.0, score)), 1)
        if not online.get(twin.device_pk, True):
            twin.status = "Offline"
        elif twin.security_score < 55:
            twin.status = "At Risk"
        elif twin.security_score < 85:
            twin.status = "Degraded"
        else:
            twin.status = "Healthy"
        twin.updated_at = now
    session.flush()
