"""Measure detection quality on simulated data (several seeds). Run: python -m scripts.evaluate"""
import numpy as np
import pandas as pd

from app.security.anomaly import AnomalyDetector
from app.security.pipeline import SecurityPipeline
from app.security.preprocessing import feature_matrix, preprocess
from tests.conftest import Gen

SCEN = ["abnormal_temperature", "suspicious_logins", "network_spike", "telemetry_manipulation"]


def run(seed: int):
    g = Gen(seed=seed)
    pipe = SecurityPipeline(AnomalyDetector().fit(feature_matrix(preprocess(g.frame(96)))))
    clean = pipe.analyze(g.frame(100, start=96))
    out = {"fp_rate": float(clean.flagged.mean()), "fp_ml": float(clean.ml_flag.mean())}
    for name in SCEN:
        rec = {"hybrid": [], "ids": [], "ml": [], "cls": []}
        for dev_pk in range(1, 25):  # one scenario per device, 24-tick window starting at tick 20
            g.params.clear()
            res = pipe.analyze(g.frame(50, start=400, scenarios={dev_pk: (name, 20, 24)}))
            w = res[res.device_pk == dev_pk].reset_index(drop=True).iloc[20:44]
            rec["hybrid"].append(w.flagged.mean())
            rec["ids"].append((w.rule_hits.str.len() > 0).mean())
            rec["ml"].append(w.ml_flag.mean())
            f = w[w.flagged]
            expect = {"abnormal_temperature": "thermal_anomaly", "suspicious_logins": "unauthorized_access",
                      "network_spike": "network_anomaly", "telemetry_manipulation": "telemetry_manipulation"}[name]
            rec["cls"].append((f.threat_class == expect).mean() if len(f) else 0.0)
        out[name] = {k: float(np.mean(v)) for k, v in rec.items()}
    return out


if __name__ == "__main__":
    runs = [run(s) for s in (11, 12, 13)]
    print(f"false-positive rate on clean data (3 seeds): hybrid {np.mean([r['fp_rate'] for r in runs]):.2%}, "
          f"ML only {np.mean([r['fp_ml'] for r in runs]):.2%}")
    print(f"{'scenario':26s} {'hybrid':>8s} {'IDS':>8s} {'IF only':>8s} {'class ok':>9s}   (share of in-scenario samples)")
    for n in SCEN:
        m = {k: np.mean([r[n][k] for r in runs]) for k in ("hybrid", "ids", "ml", "cls")}
        print(f"{n:26s} {m['hybrid']:8.0%} {m['ids']:8.0%} {m['ml']:8.0%} {m['cls']:9.0%}")
