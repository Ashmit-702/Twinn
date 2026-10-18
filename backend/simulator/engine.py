import math
from datetime import datetime

import numpy as np

from backend.simulator.profiles import CHANNELS, FLEET_MIX, PROFILES, Profile
from backend.simulator.scenarios import apply_scenario

FACILITIES = ["Pune Plant · Line 1", "Pune Plant · Line 2", "Nashik Plant · Line 1", "Nashik Plant · Line 2"]


def build_fleet(n: int, rng: np.random.Generator) -> list[dict]:
    """Deterministic list of simulated devices (all fictional)."""
    types: list[str] = []
    for key, share in FLEET_MIX:
        types += [key] * max(1, round(n * share))
    types = (types + ["cnc"] * n)[:n]
    used, fleet = set(), []
    for i, t in enumerate(types):
        p = PROFILES[t]
        while True:
            code = f"{p.prefix}-{int(rng.integers(100, 999))}"
            if code not in used:
                used.add(code)
                break
        fleet.append({
            "device_id": code, "device_type": t,
            "facility": FACILITIES[i % len(FACILITIES)],
            "ip_address": f"10.20.{i // 250}.{10 + i % 250}",
            "twin_code": str(1111800 + i),
        })
    return fleet


def make_sample(profile: Profile, ts: datetime, rng: np.random.Generator) -> dict:
    s = {}
    for ch in CHANNELS:
        if ch == "failed_logins":
            s[ch] = float(rng.poisson(0.05))
        else:
            mean, std = profile.baselines[ch]
            s[ch] = max(0.0, float(rng.normal(mean, std)))
    # gentle daily thermal cycle (0.3 sigma) so the data is not purely i.i.d.
    phase = 2 * math.pi * (ts.hour + ts.minute / 60 - 6) / 24
    s["temperature"] += 0.3 * profile.baselines["temperature"][1] * math.sin(phase)
    return s


def make_row(device: dict, ts: datetime, rng: np.random.Generator, scenario: str | None = None,
             step: int = 0, total: int = 0, params: dict | None = None) -> tuple[dict, dict]:
    """One telemetry row for a device (device needs device_pk/device_id/device_type)."""
    profile = PROFILES[device["device_type"]]
    s = make_sample(profile, ts, rng)
    params = params or {}
    if scenario:
        s, params = apply_scenario(scenario, s, profile, step, total, params, rng)
    row = {"device_pk": device["device_pk"], "device_id": device["device_id"],
           "device_type": device["device_type"], "ts": ts, "scenario": scenario, **s}
    return row, params
