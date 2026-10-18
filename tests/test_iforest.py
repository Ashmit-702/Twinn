import numpy as np

from backend.security import iforest
from backend.security.anomaly import AnomalyDetector
from backend.security.iforest import IsolationForest, c_factor
from backend.security.preprocessing import FEATURES
import pandas as pd


def test_c_factor_reference_values():
    assert c_factor(1) == 0 and c_factor(2) == 1
    assert abs(float(c_factor(256)) - 10.245) < 0.01  # 2(ln 255 + γ) − 2·255/256


def test_outliers_score_higher_than_inliers_and_scores_are_in_range():
    rng = np.random.default_rng(0)
    inliers = rng.normal(0, 1, (600, 5))
    f = IsolationForest(n_estimators=100, random_state=1).fit(inliers)
    s_in = -f.score_samples(rng.normal(0, 1, (200, 5)))
    s_out = -f.score_samples(rng.normal(8, 1, (200, 5)))
    assert 0 < s_in.min() and s_out.max() < 1
    assert s_out.mean() > s_in.mean() + 0.1
    assert (s_out > np.quantile(s_in, 0.99)).mean() > 0.95


def test_fit_is_deterministic_and_serialisation_round_trips_without_pickle():
    X = np.random.default_rng(2).normal(size=(300, 4))
    a = IsolationForest(n_estimators=30, random_state=7).fit(X)
    b = IsolationForest(n_estimators=30, random_state=7).fit(X)
    assert np.array_equal(a.score_samples(X), b.score_samples(X))
    loaded = IsolationForest.from_arrays(iforest.loads(iforest.dumps(a.arrays())))
    assert np.array_equal(a.score_samples(X), loaded.score_samples(X))


def test_detector_bytes_round_trip_and_attribution_points_at_the_deviating_feature():
    rng = np.random.default_rng(3)
    X = pd.DataFrame(rng.normal(0, 1, (800, len(FEATURES))), columns=FEATURES)
    det = AnomalyDetector(n_estimators=100).fit(X)
    det2 = AnomalyDetector.from_bytes(det.to_bytes())
    probe = pd.DataFrame(np.zeros((5, len(FEATURES))), columns=FEATURES)  # a perfectly typical row...
    probe["z_net_in_pps"] = 20.0                                          # ...with one deviating feature
    assert np.allclose(det.score(probe), det2.score(probe))
    expl, method = det2.explain(probe)
    assert method == "occlusion" and all(e[0]["feature"] == "z_net_in_pps" for e in expl)
    assert det2.explain(X.iloc[:0])[0] == []
