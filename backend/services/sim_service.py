"""Orchestrates the simulated factory: seeding history, live ticks, scenario injection."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import Device, DigitalTwin, Incident, ScenarioRun, SecurityEvent, Telemetry
from backend.security.anomaly import AnomalyDetector
from backend.security.pipeline import SecurityPipeline
from backend.security.preprocessing import feature_matrix, preprocess
from backend.services import model_store
from backend.services.incidents import auto_resolve
from backend.services.ingest import load_history, process_rows
from backend.services.twins import refresh_twins
from backend.simulator.engine import build_fleet, make_row
from backend.simulator.scenarios import SCENARIOS

ATTACKS = ["abnormal_temperature", "suspicious_logins", "network_spike", "telemetry_manipulation"]
_live_rng = np.random.default_rng()  # live ticks are intentionally non-deterministic


class SimError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _schedule(n_dev: int, ticks: int, train_ticks: int, rng: np.random.Generator) -> list[dict]:
    """Deterministic historical scenarios: some spread over the day + 4 ending in the last ~30 minutes."""
    busy: dict[int, list[tuple[int, int]]] = {}
    out: list[dict] = []

    def add(name: str, start: int, dur: int) -> bool:
        for _ in range(20):
            d = int(rng.integers(0, n_dev))
            if all(start + dur < a or start > b for a, b in busy.get(d, [])):
                busy.setdefault(d, []).append((start, start + dur))
                out.append({"scenario": name, "device_idx": d, "start": start, "duration": dur})
                return True
        return False

    for k in range(4):  # recent ones first so they get free devices
        dur = int(rng.integers(16, 22))
        add(ATTACKS[k], ticks - dur - int(rng.integers(0, 5)), dur)
    kinds = ATTACKS + ["device_dropout"]
    for k in range(max(8, n_dev // 2)):
        dur = int(rng.integers(16, 25))
        start = int(rng.integers(train_ticks + 10, max(train_ticks + 11, ticks - 40)))
        add(kinds[k % len(kinds)], start, dur)
    return out


def seed(session: Session, hours: int = 24, step_minutes: int = 5, anchor: datetime | None = None,
         wipe: bool = True) -> dict:
    """(Re)create the fleet, 24h of history with scenarios, train the model, run detection over history."""
    s = get_settings()
    rng = np.random.default_rng(s.sim_seed)
    ticks = hours * 60 // step_minutes
    train_ticks = max(96, ticks // 3)
    if ticks < train_ticks + 60:
        raise SimError("hours too small; use at least 12")

    if wipe:
        if session.get_bind().dialect.name == "postgresql":
            session.execute(text("TRUNCATE incidents, security_events, scenario_runs, telemetry, digital_twins, "
                                 "devices RESTART IDENTITY CASCADE"))
        else:
            for table in (Incident, SecurityEvent, ScenarioRun, Telemetry, DigitalTwin, Device):
                session.execute(delete(table))
    fleet = build_fleet(s.sim_device_count, rng)
    devices = [Device(device_id=f["device_id"], device_type=f["device_type"], facility=f["facility"],
                      ip_address=f["ip_address"], is_online=True) for f in fleet]
    session.add_all(devices)
    session.flush()
    session.add_all(DigitalTwin(twin_code=f["twin_code"], device_pk=d.id) for f, d in zip(fleet, devices))
    devs = [{"device_pk": d.id, "device_id": d.device_id, "device_type": d.device_type} for d in devices]

    end = (anchor or _now()).replace(second=0, microsecond=0)
    stamps = [end - timedelta(minutes=step_minutes * (ticks - 1 - k)) for k in range(ticks)]
    sched = _schedule(len(devs), ticks, train_ticks, rng)
    by_dev: dict[int, list[dict]] = {}
    for sc in sched:
        by_dev.setdefault(sc["device_idx"], []).append({**sc, "params": {}})

    rows: list[dict] = []
    for k, ts in enumerate(stamps):
        for di, dev in enumerate(devs):
            act = next((x for x in by_dev.get(di, []) if x["start"] <= k < x["start"] + x["duration"]), None)
            if act and act["scenario"] == "device_dropout":
                continue
            row, act_params = make_row(dev, ts, rng, act["scenario"] if act else None,
                                       k - act["start"] if act else 0, act["duration"] if act else 0,
                                       act["params"] if act else None)
            if act:
                act["params"] = act_params
            rows.append(row)

    train_df = pd.DataFrame([r for r in rows if r["ts"] < stamps[train_ticks]])
    assert train_df["scenario"].isna().all()  # baseline is clean by construction
    detector = AnomalyDetector().fit(feature_matrix(preprocess(train_df)))
    model_store.set_detector(session, detector, {"trained_on": "seed_clean_baseline", "rows": len(train_df)})
    result = process_rows(session, SecurityPipeline(detector), rows)

    last = {r["device_pk"]: r["ts"] for r in rows}
    for d in devices:
        d.last_seen = last.get(d.id)
    refresh_twins(session, end, s.active_window_minutes)
    auto_resolve(session, end, s.active_window_minutes)
    session.commit()
    return {**result, "devices": len(devices), "hours": hours, "train_rows": len(train_df),
            "scheduled_scenarios": len(sched)}


def tick(session: Session, count: int = 1) -> dict:
    pipeline = model_store.get_pipeline(session)
    devices = list(session.scalars(select(Device).order_by(Device.id)))
    if not devices:
        raise model_store.ModelNotReady("No simulated devices yet. Run seed first.")
    runs = list(session.scalars(select(ScenarioRun).where(ScenarioRun.status == "active")))
    last_ts = session.scalar(select(func.max(Telemetry.ts)))
    base = max(_now(), (last_ts + timedelta(seconds=1)) if last_ts else _now())

    rows: list[dict] = []
    for i in range(count):
        ts = base + timedelta(seconds=i)
        active = {r.device_pk: r for r in runs if r.status == "active"}
        for dev in devices:
            run = active.get(dev.id)
            if run and run.scenario == "device_dropout":
                dev.is_online = False
                continue
            dev.is_online, dev.last_seen = True, ts
            row, params = make_row({"device_pk": dev.id, "device_id": dev.device_id, "device_type": dev.device_type},
                                   ts, _live_rng, run.scenario if run else None,
                                   run.ticks_done if run else 0, run.total_ticks if run else 0,
                                   dict(run.params) if run else None)
            if run:
                run.params = params
            rows.append(row)
        for run in active.values():
            run.ticks_done += 1
            if run.ticks_done >= run.total_ticks:
                run.status = "finished"
                if run.scenario == "device_dropout":
                    next(d for d in devices if d.id == run.device_pk).is_online = True

    result = process_rows(session, pipeline, rows, load_history(session))
    now = _now()
    refresh_twins(session, now, get_settings().active_window_minutes)
    auto_resolve(session, now, get_settings().active_window_minutes)
    purge_old_telemetry(session)  # commits; bounds table growth since there is no background job
    return {**result, "ticks": count}


def inject_scenario(session: Session, scenario: str, device_id: str, duration_ticks: int) -> ScenarioRun:
    if scenario not in SCENARIOS:
        raise SimError(f"Unknown scenario '{scenario}'")
    dev = session.scalar(select(Device).where(Device.device_id == device_id))
    if dev is None:
        raise SimError(f"Unknown device '{device_id}'")
    if session.scalar(select(ScenarioRun).where(ScenarioRun.device_pk == dev.id, ScenarioRun.status == "active")):
        raise SimError(f"{device_id} already has an active scenario")
    run = ScenarioRun(scenario=scenario, device_pk=dev.id, total_ticks=duration_ticks, ticks_done=0,
                      status="active", params={}, created_at=_now())
    session.add(run)
    session.commit()
    return run


def purge_old_telemetry(session: Session) -> int:
    cutoff = _now() - timedelta(hours=get_settings().retention_hours)
    n = session.execute(delete(Telemetry).where(Telemetry.ts < cutoff)).rowcount
    session.commit()
    return n
