import numpy as np
import pandas as pd
import pytest

from backend.security import ids
from backend.security.anomaly import AnomalyDetector
from backend.security.classifier import classify
from backend.security.pipeline import SecurityPipeline
from backend.security.preprocessing import FEATURES, feature_matrix, preprocess
from backend.security.risk import risk_score, severity
from tests.conftest import Gen

ATTACKS = {"abnormal_temperature": "thermal_anomaly", "suspicious_logins": "unauthorized_access",
           "network_spike": "network_anomaly", "telemetry_manipulation": "telemetry_manipulation"}


@pytest.fixture(scope="module")
def pipe():
    g = Gen(seed=3)
    det = AnomalyDetector().fit(feature_matrix(preprocess(g.frame(96))))
    return g, SecurityPipeline(det)


def test_preprocess_handles_missing_values():
    g = Gen(seed=5, n_devices=5)
    df = g.frame(12)
    df.loc[3, "temperature"] = np.nan
    df["pressure"] = df["pressure"].astype(object)
    df.loc[7, "pressure"] = "bad"
    out = preprocess(df)
    assert out[FEATURES].fillna(1.0).notna().all().all()


def test_false_positive_rate_on_clean_data_is_low(pipe):
    g, p = pipe
    res = p.analyze(g.frame(100, start=96))
    assert res["flagged"].mean() < 0.01  # measured ~0.1% with seed 3; threshold leaves headroom


@pytest.mark.parametrize("scenario,expected", ATTACKS.items())
def test_scenario_is_detected_and_classified(pipe, scenario, expected):
    g, p = pipe
    g.params.clear()
    res = p.analyze(g.frame(60, start=300, scenarios={1: (scenario, 20, 24)}))
    window = res[(res.device_pk == 1)].reset_index(drop=True).iloc[20:44]
    flagged = window[window.flagged]
    assert len(flagged) >= 0.5 * len(window)
    assert (flagged.threat_class == expected).mean() >= 0.6
    outside = res[(res.device_pk == 1)].reset_index(drop=True)
    assert outside.iloc[:20].flagged.sum() <= 1  # little/no alarm before the scenario starts


def test_ml_only_detection_and_shap_explanations(pipe):
    g, p = pipe
    g.params.clear()
    res = p.analyze(g.frame(40, start=500, scenarios={2: ("network_spike", 10, 20)}))
    row = res[res.flagged & (res.device_pk == 2)].iloc[0]
    assert row["explain_method"] == "shap"
    assert row["explanation"][0]["feature"] in FEATURES
    assert row["explanation"][0]["contribution"] > 0


def test_rules_fire_on_crafted_rows():
    df = pd.DataFrame({"z_temperature": [7, 0], "net_in_pps": [100, 1000], "mean_net_in_pps": [100, 100],
                       "failed_logins": [0, 6], "rstd_temperature": [1, np.nan], "rstd_pressure": [1, np.nan]})
    r = ids.evaluate(df)
    assert r.loc[0, "R-TEMP-HIGH"] and not r.loc[1, "R-TEMP-HIGH"]
    assert r.loc[1, "R-NET-SPIKE"] and r.loc[1, "R-LOGIN-BURST"]
    assert not r["R-TELEMETRY-FLATLINE"].any()  # NaN (incomplete window) must not fire


def test_classifier_priority_and_ml_fallback():
    assert classify(["R-TEMP-HIGH", "R-LOGIN-BURST"], []) == "unauthorized_access"
    assert classify([], ["z_net_in_pps", "z_temperature"]) == "network_anomaly"
    assert classify([], ["z_cpu_load"]) == "unclassified_anomaly"


def test_risk_and_severity_are_monotonic_and_bounded():
    low = risk_score(20, False, "unclassified_anomaly", 0.5)
    high = risk_score(90, True, "telemetry_manipulation", 1.0)
    assert 0 <= low < high <= 100
    assert [severity(x) for x in (10, 45, 68, 78)] == ["Low", "Medium", "High", "Critical"]
