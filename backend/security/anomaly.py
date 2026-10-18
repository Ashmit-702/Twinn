"""Isolation Forest anomaly detection with SHAP explanations."""
import io
import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.security.preprocessing import FEATURES

log = logging.getLogger(__name__)


class AnomalyDetector:
    """Trained on known-clean baseline data only.

    Raw IF score is mapped to 0-100 so that the median training sample is 0 and the
    99.9th percentile of training samples is 50. Scores >= `threshold` (50) are flagged.
    """

    threshold = 50.0

    def __init__(self, n_estimators: int = 200, random_state: int = 42):
        self.model = IsolationForest(n_estimators=n_estimators, contamination="auto", random_state=random_state)
        self.med = 0.0
        self.hi = 1.0
        self._explainer = None

    def fit(self, X: pd.DataFrame) -> "AnomalyDetector":
        self.model.fit(X[FEATURES])
        raw = -self.model.score_samples(X[FEATURES])
        self.med = float(np.median(raw))
        self.hi = float(np.quantile(raw, 0.999))
        if self.hi <= self.med:
            self.hi = self.med + 1e-6
        self._explainer = None
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        raw = -self.model.score_samples(X[FEATURES])
        return np.clip(50.0 * (raw - self.med) / (self.hi - self.med), 0, 100)

    def explain(self, X: pd.DataFrame, top_k: int = 3) -> tuple[list[list[dict]], str]:
        """Top features pushing each row toward 'anomalous'. Returns (explanations, method)."""
        if len(X) == 0:
            return [], "shap"
        try:
            if self._explainer is None:
                import shap  # lazy: keeps cold starts fast when nothing needs explaining
                self._explainer = shap.TreeExplainer(self.model)
            sv = np.asarray(self._explainer.shap_values(X[FEATURES]))
            contrib = -sv  # IF output is higher for normal points -> negate so + = more anomalous
            method = "shap"
        except Exception as exc:  # pragma: no cover - defensive fallback, reported in the event details
            log.warning("SHAP failed (%s); falling back to absolute deviation", exc)
            contrib = X[FEATURES].abs().to_numpy()
            method = "abs_deviation"
        out = []
        for row in contrib:
            idx = np.argsort(-row)[:top_k]
            out.append([{"feature": FEATURES[i], "contribution": round(float(row[i]), 4)} for i in idx])
        return out, method

    def to_bytes(self) -> bytes:
        buf = io.BytesIO()
        joblib.dump({"model": self.model, "med": self.med, "hi": self.hi}, buf, compress=3)
        return buf.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "AnomalyDetector":
        """Only ever call with bytes produced by to_bytes() and stored in our own database (pickle-based)."""
        obj = joblib.load(io.BytesIO(data))
        d = cls()
        d.model, d.med, d.hi = obj["model"], obj["med"], obj["hi"]
        return d
