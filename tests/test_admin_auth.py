import os

import pytest

if not os.environ.get("TEST_DATABASE_URL"):
    pytest.skip("Set TEST_DATABASE_URL (a *_test PostgreSQL database) to run admin-auth tests", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from backend.config import get_settings  # noqa: E402

KEY = "test-admin-key-123"


@pytest.fixture()
def client(monkeypatch):
    # Trailing newline/space on the server value must not break matching (common when pasted into env settings).
    monkeypatch.setenv("ADMIN_API_KEY", f" {KEY}\n")
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    monkeypatch.delenv("ADMIN_API_KEY")
    get_settings.cache_clear()


def _open_incident(c):
    c.post("/api/simulator/seed", json={"hours": 24}, headers={"X-Admin-Key": KEY})
    dev = next(d for d in c.get("/api/simulator/devices").json() if d["device_type"] == "plc")["device_id"]
    c.post("/api/simulator/scenarios", json={"scenario": "suspicious_logins", "device_id": dev, "duration_ticks": 20},
           headers={"X-Admin-Key": KEY})
    c.post("/api/simulator/tick", json={"count": 20}, headers={"X-Admin-Key": KEY})
    open_ = c.get("/api/incidents?status=open").json()
    assert open_, "expected an open incident"
    return open_[0]["id"]


def test_writes_require_valid_admin_key(client):
    assert client.post("/api/simulator/tick", json={"count": 1}).status_code == 401
    assert client.post("/api/simulator/tick", json={"count": 1}, headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.post("/api/simulator/seed", json={"hours": 24}, headers={"X-Admin-Key": KEY}).status_code == 200


def test_resolve_incident_with_key(client):
    iid = _open_incident(client)
    assert client.patch(f"/api/incidents/{iid}/resolve").status_code == 401
    assert client.patch(f"/api/incidents/{iid}/resolve", headers={"X-Admin-Key": f"  {KEY} "}).status_code == 200
    assert iid not in [i["id"] for i in client.get("/api/incidents?status=open").json()]
    assert iid in [i["id"] for i in client.get("/api/incidents?status=resolved").json()]
    assert client.patch("/api/incidents/99999999/resolve", headers={"X-Admin-Key": KEY}).status_code == 404
