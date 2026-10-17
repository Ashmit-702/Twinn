"""Controlled attack / fault scenarios injected into otherwise normal telemetry."""
import numpy as np

from app.simulator.profiles import Profile

SCENARIOS = {
    "abnormal_temperature": "Temperature ramps far above normal (overheating / process tampering).",
    "suspicious_logins": "Burst of failed logins plus elevated command rate (brute-force attempt).",
    "network_spike": "Inbound/outbound packet-rate spike with CPU load (flood / scan).",
    "telemetry_manipulation": "Temperature & pressure frozen (replayed) while hidden load rises.",
    "device_dropout": "Device stops reporting and goes offline.",
}


def apply_scenario(name: str, s: dict, profile: Profile, step: int, total: int,
                   params: dict, rng: np.random.Generator) -> tuple[dict, dict]:
    """Mutate one telemetry sample according to `name`. Returns (sample, params)."""
    b = profile.baselines
    if name == "abnormal_temperature":
        ramp = min(1.0, (step + 1) / max(1.0, 0.4 * total))
        s["temperature"] += ramp * 0.5 * b["temperature"][0]
        s["vibration"] += ramp * 3 * b["vibration"][1]
    elif name == "suspicious_logins":
        s["failed_logins"] = float(rng.poisson(12))
        s["cmd_rate"] += 4 * b["cmd_rate"][1]
    elif name == "network_spike":
        s["net_in_pps"] *= rng.uniform(5, 9)
        s["net_out_pps"] *= rng.uniform(2, 4)
        s["cpu_load"] = min(100.0, s["cpu_load"] + 25)
    elif name == "telemetry_manipulation":
        if "frozen_temperature" not in params:
            params = {**params, "frozen_temperature": s["temperature"], "frozen_pressure": s["pressure"]}
        s["temperature"] = params["frozen_temperature"]
        s["pressure"] = params["frozen_pressure"]
        s["vibration"] *= 1.8  # the real (hidden) condition keeps evolving
        s["cpu_load"] += 15
    return s, params
