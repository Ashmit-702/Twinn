"""Run the security pipeline on new telemetry rows and persist telemetry, events and incidents."""
import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Device, SecurityEvent, Telemetry
from app.security.pipeline import SecurityPipeline
from app.security.preprocessing import WINDOW
from app.services.incidents import update_incidents
from app.simulator.profiles import CHANNELS

TELEMETRY_COLS = ["device_pk", "ts", *CHANNELS, "anomaly_score", "scenario"]


def load_history(session: Session, n: int = WINDOW - 1) -> pd.DataFrame:
    """Last n telemetry rows per device, needed for rolling features on live ticks."""
    rn = func.row_number().over(partition_by=Telemetry.device_pk, order_by=Telemetry.ts.desc()).label("rn")
    sub = select(Telemetry.device_pk, Telemetry.ts, *[getattr(Telemetry, c) for c in CHANNELS], rn).subquery()
    q = (select(sub, Device.device_id, Device.device_type)
         .join(Device, Device.id == sub.c.device_pk).where(sub.c.rn <= n))
    return pd.DataFrame(session.execute(q).mappings().all())


def process_rows(session: Session, pipeline: SecurityPipeline, rows: list[dict],
                 history: pd.DataFrame | None = None) -> dict:
    if not rows:
        return {"telemetry": 0, "events": 0, "incidents_opened": 0}
    df = pd.DataFrame(rows)
    df["_i"], df["is_new"] = range(len(df)), True
    if history is not None and len(history):
        h = history.copy()
        h["_i"], h["is_new"] = -1, False
        df = pd.concat([h, df], ignore_index=True)

    res = pipeline.analyze(df)
    new = res[res["is_new"]].set_index("_i").sort_index()
    for r, score in zip(rows, new["anomaly_score"]):
        r["anomaly_score"] = float(score)

    tele = [{k: r.get(k) for k in TELEMETRY_COLS} for r in rows]
    for i in range(0, len(tele), 5000):
        session.execute(insert(Telemetry), tele[i:i + 5000])

    events, critical = [], []
    for _, r in new[new["flagged"]].iterrows():
        ev = {"ts": r["ts"].to_pydatetime(), "device_pk": int(r["device_pk"]), "event_type": r["event_type"],
              "threat_class": r["threat_class"], "severity": r["severity"], "source": r["source"],
              "anomaly_score": round(float(r["anomaly_score"]), 1), "risk_score": float(r["risk_score"]),
              "rule_ids": list(r["rule_hits"]),
              "details": {"features": {c: round(float(r[c]), 3) for c in CHANNELS},
                          "explanation": r["explanation"], "explain_method": r["explain_method"]}}
        events.append(ev)
        if ev["severity"] == "Critical":
            critical.append({**ev, "device_id": r["device_id"]})
    if events:
        session.execute(insert(SecurityEvent), events)
    opened = update_incidents(session, critical, get_settings().active_window_minutes)
    return {"telemetry": len(rows), "events": len(events), "incidents_opened": opened}
