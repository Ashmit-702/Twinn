import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone

from app.simulator.engine import build_fleet, make_row

TEST_DB = os.environ.get("TEST_DATABASE_URL")
if TEST_DB:
    # Safety: API tests TRUNCATE tables, so only ever run against a database whose name ends in _test.
    assert TEST_DB.split("?")[0].rsplit("/", 1)[-1].endswith("_test"), "TEST_DATABASE_URL must point to a *_test database"
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ["MODEL_DIR"] = tempfile.mkdtemp(prefix="twin_model_")
    os.environ["ENVIRONMENT"] = "development"
    os.environ["ADMIN_API_KEY"] = ""

T0 = datetime(2026, 10, 18, 0, 0, tzinfo=timezone.utc)


class Gen:
    """In-memory telemetry generator for pure (no DB) pipeline tests."""

    def __init__(self, seed=1, n_devices=24):
        self.rng = np.random.default_rng(seed)
        self.fleet = build_fleet(n_devices, self.rng)
        for i, d in enumerate(self.fleet):
            d["device_pk"] = i + 1
        self.params = {}

    def frame(self, ticks, start=0, scenarios=None):
        """scenarios: {device_pk: (name, start_tick, duration)} relative to this frame."""
        rows = []
        for k in range(ticks):
            for d in self.fleet:
                ts = T0 + timedelta(minutes=5 * (start + k))
                sc = (scenarios or {}).get(d["device_pk"])
                if sc and sc[1] <= k < sc[1] + sc[2]:
                    r, p = make_row(d, ts, self.rng, sc[0], k - sc[1], sc[2], self.params.get(d["device_pk"], {}))
                    self.params[d["device_pk"]] = p
                else:
                    r, _ = make_row(d, ts, self.rng)
                rows.append(r)
        return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def gen():
    return Gen()
