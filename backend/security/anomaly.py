"""Isolation Forest anomaly detector with feature attribution (NumPy only; see iforest.py for why)."""
import numpy as np
import pandas as pd

from backend.security import iforest
from backend.security.preprocessing import FEATURES


class AnomalyDetector:
    """Trained on known-clean baseline data only.

    The raw forest score is mapped to 0-100 so that the median training sample is 0 and the 99.9th
    percentile of training samples is 50. Scores >= `threshold` (50) are flagged.
    """

    threshold = 50.0

    def __init__(self, n_estimators: int = 200, random_state: int = 42):
        self.model = iforest.IsolationForest(n_estimators=n_estimators, random_state=random_state)
        self.med = 0.0
        self.hi = 1.0
        self.baseline = np.zeros(len(FEATURES))

    def _scaled(self, Xv: np.ndarray) -> np.ndarray:
        raw = -self.model.score_samples(Xv)
        return 50.0 * (raw - self.med) / (self.hi - self.med)

    def fit(self, X: pd.DataFrame) -> "AnomalyDetector":
        Xv = X[FEATURES].to_numpy(dtype=float)
        self.model.fit(Xv)
        raw = -self.model.score_samples(Xv)
        self.med = float(np.median(raw))
        self.hi = float(np.quantile(raw, 0.999))
        if self.hi <= self.med:
            self.hi = self.med + 1e-6
        self.baseline = np.median(Xv, axis=0)  # reference ("normal") value per feature for attribution
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return np.clip(self._scaled(X[FEATURES].to_numpy(dtype=float)), 0, 100)

    def explain(self, X: pd.DataFrame, top_k: int = 3) -> tuple[list[list[dict]], str]:
        """Occlusion attribution: how much does the anomaly score drop if one feature is reset to its
        normal (training-median) value? Only features that push toward 'anomalous' are reported.
        This is a model-specific, single-feature counterfactual, not SHAP (SHAP's scikit-learn/SciPy
        dependency chain does not fit in a Vercel function); it can under-credit anomalies that need
        several features at once."""
        if len(X) == 0:
            return [], "occlusion"
        Xv = X[FEATURES].to_numpy(dtype=float)
        base = self._scaled(Xv)
        contrib = np.zeros_like(Xv)
        for j in range(Xv.shape[1]):
            occluded = Xv.copy()
            occluded[:, j] = self.baseline[j]
            contrib[:, j] = base - self._scaled(occluded)
        out = []
        for row in contrib:
            order = [i for i in np.argsort(-row)[:top_k] if row[i] > 1e-9]
            out.append([{"feature": FEATURES[i], "contribution": round(float(row[i]), 4)} for i in order])
        return out, "occlusion"

    def to_bytes(self) -> bytes:
        return iforest.dumps({**self.model.arrays(), "med": np.array(self.med), "hi": np.array(self.hi),
                              "baseline": self.baseline})

    @classmethod
    def from_bytes(cls, data: bytes) -> "AnomalyDetector":
        a = iforest.loads(data)  # numpy arrays only: loading never executes code
        d = cls()
        d.model = iforest.IsolationForest.from_arrays(a)
        d.med, d.hi, d.baseline = float(a["med"]), float(a["hi"]), a["baseline"]
        return d
