import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("Set TEST_DATABASE_URL (a *_test PostgreSQL database) to run API tests", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.api import deps  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Device, DigitalTwin, SecurityEvent, Telemetry  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        r = c.post("/api/simulator/seed", json={"hours": 24})
        assert r.status_code == 200, r.text
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_dashboard_numbers_match_database(client):
    s = client.get("/api/dashboard/summary").json()
    with SessionLocal() as db:
        assert s["active_twins"] == db.scalar(select(func.count(DigitalTwin.id)))
        assert s["devices"]["total"] == db.scalar(select(func.count(Device.id))) == 24
    assert s["devices"]["online"] + s["devices"]["offline"] == s["devices"]["total"]
    ds = client.get("/api/dashboard/device-status").json()
    assert ds["online"] + ds["offline"] + ds["alerting"] == ds["total"]
    dist = client.get("/api/dashboard/anomaly-distribution").json()
    assert sum(b["devices"] for b in dist) == 24 and len(dist) == 10
    assert len(client.get("/api/dashboard/threats-timeline?hours=24").json()) == 24


def test_seed_creates_events_with_explanations(client):
    ev = client.get("/api/dashboard/events?limit=5").json()
    assert ev and {"ts", "event_type", "severity", "source_device"} <= ev[0].keys()
    with SessionLocal() as db:
        e = db.scalars(select(SecurityEvent).limit(1)).one()
        assert e.details["explanation"] and e.details["explain_method"] in ("shap", "abs_deviation")


def test_injected_scenario_changes_dashboard_data(client):
    dev = next(d for d in client.get("/api/simulator/devices").json() if d["device_type"] == "plc")["device_id"]
    with SessionLocal() as db:
        before = db.scalar(select(func.count(SecurityEvent.id)))
    r = client.post("/api/simulator/scenarios", json={"scenario": "suspicious_logins", "device_id": dev, "duration_ticks": 15})
    assert r.status_code == 200
    assert client.post("/api/simulator/scenarios", json={"scenario": "network_spike", "device_id": dev}).status_code == 400
    t = client.post("/api/simulator/tick", json={"count": 15}).json()
    assert t["events"] > 0
    with SessionLocal() as db:
        assert db.scalar(select(func.count(SecurityEvent.id))) == before + t["events"]
    top = client.get("/api/dashboard/events?limit=20").json()
    assert any(e["source_device"] == dev and e["threat_class"] == "unauthorized_access" for e in top)


def test_dropout_marks_device_offline_then_recovers(client):
    dev = client.get("/api/simulator/devices").json()[3]["device_id"]
    client.post("/api/simulator/scenarios", json={"scenario": "device_dropout", "device_id": dev, "duration_ticks": 5})
    client.post("/api/simulator/tick", json={"count": 2})
    assert client.get("/api/dashboard/summary").json()["devices"]["offline"] == 1
    client.post("/api/simulator/tick", json={"count": 5})
    assert client.get("/api/dashboard/summary").json()["devices"]["offline"] == 0


def test_unknown_scenario_and_device_rejected(client):
    assert client.post("/api/simulator/scenarios", json={"scenario": "nope", "device_id": "x"}).status_code == 400
    assert client.post("/api/simulator/tick", json={"count": 0}).status_code == 422


def test_admin_key_enforced_when_configured(client, monkeypatch):
    class S:
        admin_api_key, environment = "s3cret", "production"
    monkeypatch.setattr(deps, "get_settings", lambda: S())
    assert client.post("/api/simulator/tick", json={"count": 1}).status_code == 401
    assert client.post("/api/simulator/tick", json={"count": 1}, headers={"X-Admin-Key": "bad"}).status_code == 401
    assert client.post("/api/simulator/tick", json={"count": 1}, headers={"X-Admin-Key": "s3cret"}).status_code == 200
    assert client.get("/api/dashboard/summary").status_code == 200  # reads stay public

    class P:
        admin_api_key, environment = "", "production"
    monkeypatch.setattr(deps, "get_settings", lambda: P())
    assert client.post("/api/simulator/tick", json={"count": 1}).status_code == 403


def test_cors_only_allows_configured_origin(client):
    ok = client.options("/api/dashboard/summary", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/dashboard/summary", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_model_is_retrained_from_stored_baseline_if_missing(client):
    import shutil

    from app.config import get_settings
    from app.services import model_store

    model_store.set_detector(None, persist=False)
    shutil.rmtree(get_settings().model_dir, ignore_errors=True)
    assert client.post("/api/simulator/tick", json={"count": 1}).status_code == 200
