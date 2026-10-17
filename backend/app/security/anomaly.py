"""Isolation Forest anomaly detection with SHAP explanations."""
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest

from app.security.preprocessing import FEATURES

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

    def save(self, directory: str) -> None:
        Path(directory).mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "med": self.med, "hi": self.hi}, Path(directory) / "isolation_forest.joblib")

    @classmethod
    def load(cls, directory: str) -> "AnomalyDetector | None":
        p = Path(directory) / "isolation_forest.joblib"
        if not p.exists():
            return None
        data = joblib.load(p)
        d = cls()
        d.model, d.med, d.hi = data["model"], data["med"], data["hi"]
        return d
