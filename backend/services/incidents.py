from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models import Incident


def update_incidents(session: Session, critical_events: list[dict], window_minutes: int) -> int:
    """Open/extend one incident per (device, threat class) for Critical events. Returns #new incidents."""
    if not critical_events:
        return 0
    window = timedelta(minutes=window_minutes)
    open_by_key = {(i.device_pk, i.threat_class): i
                   for i in session.scalars(select(Incident).where(Incident.status == "open"))}
    created = 0
    for ev in sorted(critical_events, key=lambda e: e["ts"]):
        key = (ev["device_pk"], ev["threat_class"])
        inc = open_by_key.get(key)
        if inc is not None and ev["ts"] - inc.last_event_at > window:
            inc.status, inc.resolved_at = "resolved", inc.last_event_at
            inc = None
        if inc is None:
            inc = Incident(title=f'{ev["event_type"]} on {ev["device_id"]}', device_pk=ev["device_pk"],
                           threat_class=ev["threat_class"], severity="Critical", status="open",
                           opened_at=ev["ts"], last_event_at=ev["ts"], event_count=1)
            session.add(inc)
            open_by_key[key] = inc
            created += 1
        else:
            inc.last_event_at, inc.event_count = ev["ts"], inc.event_count + 1
    session.flush()
    return created


def auto_resolve(session: Session, now: datetime, window_minutes: int) -> None:
    """Close incidents that have had no new Critical event within the active window."""
    session.execute(update(Incident)
                    .where(Incident.status == "open", Incident.last_event_at < now - timedelta(minutes=window_minutes))
                    .values(status="resolved", resolved_at=now))
