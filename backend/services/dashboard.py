"""Read-side queries for the dashboard. Every number returned here is computed from the database."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Device, DigitalTwin, Incident, SecurityEvent, Telemetry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _active_groups(session: Session, now: datetime) -> set[tuple[int, str, str]]:
    since = now - timedelta(minutes=get_settings().active_window_minutes)
    q = (select(SecurityEvent.device_pk, SecurityEvent.threat_class, SecurityEvent.severity).distinct()
         .where(SecurityEvent.ts >= since, SecurityEvent.severity.in_(["High", "Critical"])))
    best: dict[tuple[int, str], str] = {}
    for dev, cls, sev in session.execute(q):
        if best.get((dev, cls)) != "Critical":
            best[(dev, cls)] = sev
    return {(d, c, s) for (d, c), s in best.items()}


def summary(session: Session) -> dict:
    now = _now()
    total = session.scalar(select(func.count(Device.id))) or 0
    offline = session.scalar(select(func.count(Device.id)).where(Device.is_online.is_(False))) or 0
    groups = _active_groups(session, now)
    crit_inc = session.scalar(select(func.count(Incident.id)).where(Incident.status == "open",
                                                                     Incident.severity == "Critical")) or 0
    open_inc = session.scalar(select(func.count(Incident.id)).where(Incident.status == "open")) or 0
    return {
        "active_twins": session.scalar(select(func.count(DigitalTwin.id))) or 0,
        "devices": {"total": total, "online": total - offline, "offline": offline},
        "active_threats": {"total": len(groups),
                           "critical": sum(1 for g in groups if g[2] == "Critical"),
                           "high": sum(1 for g in groups if g[2] == "High")},
        "critical_incidents": crit_inc,
        "open_incidents": open_inc,
        "window_minutes": get_settings().active_window_minutes,
        "server_time": now.isoformat(),
    }


def twins(session: Session, limit: int = 50) -> list[dict]:
    q = (select(DigitalTwin, Device).join(Device, Device.id == DigitalTwin.device_pk)
         .order_by(DigitalTwin.security_score, DigitalTwin.twin_code).limit(limit))
    return [{"twin_code": t.twin_code, "device_id": d.device_id, "device_type": d.device_type,
             "facility": d.facility, "status": t.status, "security_score": t.security_score}
            for t, d in session.execute(q)]


def events(session: Session, limit: int = 20) -> list[dict]:
    q = (select(SecurityEvent, Device.device_id).join(Device, Device.id == SecurityEvent.device_pk)
         .order_by(SecurityEvent.ts.desc(), SecurityEvent.id.desc()).limit(limit))
    return [{"id": e.id, "ts": e.ts.isoformat(), "event_type": e.event_type, "severity": e.severity,
             "source_device": dev, "threat_class": e.threat_class, "risk_score": e.risk_score,
             "anomaly_score": e.anomaly_score, "source": e.source} for e, dev in session.execute(q)]


def threats_timeline(session: Session, hours: int = 24) -> list[dict]:
    now = _now()
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
    bucket = func.date_trunc("hour", SecurityEvent.ts)
    high = SecurityEvent.severity.in_(["High", "Critical"])
    q = (select(bucket, func.count().filter(SecurityEvent.severity != "Low"), func.count().filter(high))
         .where(SecurityEvent.ts >= start).group_by(bucket))
    got = {b: (t, h) for b, t, h in session.execute(q)}
    out = []
    for i in range(hours):
        b = start + timedelta(hours=i)
        t, h = got.get(b, (0, 0))
        out.append({"ts": b.isoformat(), "threats": t, "high_severity": h})
    return out


def anomaly_distribution(session: Session) -> list[dict]:
    last = select(Telemetry.device_pk, func.max(Telemetry.ts).label("ts")).group_by(Telemetry.device_pk).subquery()
    scores = session.scalars(select(Telemetry.anomaly_score).join(
        last, (Telemetry.device_pk == last.c.device_pk) & (Telemetry.ts == last.c.ts))).all()
    bins = [0] * 10
    for sc in scores:
        if sc is not None:
            bins[min(int(sc // 10), 9)] += 1
    return [{"bin": i * 10, "devices": n} for i, n in enumerate(bins)]


def device_status(session: Session) -> dict:
    now = _now()
    total = session.scalar(select(func.count(Device.id))) or 0
    offline_ids = set(session.scalars(select(Device.id).where(Device.is_online.is_(False))))
    alerting_ids = {g[0] for g in _active_groups(session, now)} - offline_ids
    offline, alerting = len(offline_ids), len(alerting_ids)
    online = total - offline - alerting
    pct = (lambda n: round(100 * n / total, 1)) if total else (lambda n: 0.0)
    return {"total": total, "online": online, "offline": offline, "alerting": alerting,
            "online_pct": pct(online), "offline_pct": pct(offline), "alerting_pct": pct(alerting)}
