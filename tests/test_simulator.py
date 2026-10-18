import numpy as np

from backend.simulator.engine import build_fleet, make_row
from backend.simulator.profiles import PROFILES
from tests.conftest import T0


def _dev(t):
    return {"device_pk": 1, "device_id": "X-1", "device_type": t}


def test_fleet_is_deterministic_unique_and_covers_all_types():
    a = build_fleet(24, np.random.default_rng(7))
    b = build_fleet(24, np.random.default_rng(7))
    assert a == b
    assert len({d["device_id"] for d in a}) == 24
    assert {d["device_type"] for d in a} == set(PROFILES)


def test_normal_samples_stay_near_baseline():
    rng = np.random.default_rng(0)
    for t, p in PROFILES.items():
        temps = [make_row(_dev(t), T0, rng)[0]["temperature"] for _ in range(300)]
        mean, std = p.baselines["temperature"]
        assert abs(np.mean(temps) - mean) < 0.5 * std + 0.1
        assert min(temps) > 0


def test_each_scenario_changes_the_expected_channel():
    rng = np.random.default_rng(0)
    d = _dev("cnc")
    base = make_row(d, T0, rng)[0]
    hot = make_row(d, T0, rng, "abnormal_temperature", 20, 20)[0]
    assert hot["temperature"] > base["temperature"] + 20
    assert make_row(d, T0, rng, "suspicious_logins", 0, 20)[0]["failed_logins"] >= 3
    assert make_row(d, T0, rng, "network_spike", 0, 20)[0]["net_in_pps"] > 3 * PROFILES["cnc"].baselines["net_in_pps"][0]


def test_telemetry_manipulation_freezes_readings():
    rng = np.random.default_rng(0)
    d, params, temps = _dev("plc"), {}, []
    for step in range(10):
        row, params = make_row(d, T0, rng, "telemetry_manipulation", step, 10, params)
        temps.append(row["temperature"])
    assert len(set(temps)) == 1
