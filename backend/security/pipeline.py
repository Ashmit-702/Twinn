"""preprocessing -> Isolation Forest -> rule IDS -> classification -> risk. Pure (no DB)."""
import pandas as pd

from backend.security import ids
from backend.security.anomaly import AnomalyDetector
from backend.security.classifier import EVENT_TYPES, classify
from backend.security.preprocessing import feature_matrix, preprocess
from backend.security.risk import risk_score, severity
from backend.simulator.profiles import PROFILES


class SecurityPipeline:
    def __init__(self, detector: AnomalyDetector):
        self.detector = detector

    def analyze(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Returns the preprocessed frame plus: anomaly_score, rule_hits, ml_flag, flagged and, for flagged
        rows, threat_class, event_type, risk_score, severity, source, explanation, explain_method."""
        df = preprocess(raw)
        X = feature_matrix(df)
        df["anomaly_score"] = self.detector.score(X)
        hits = ids.evaluate(df)
        df["rule_hits"] = hits.apply(lambda r: [c for c in hits.columns if r[c]], axis=1)
        df["ml_flag"] = df["anomaly_score"] >= self.detector.threshold
        df["flagged"] = df["ml_flag"] | (df["rule_hits"].str.len() > 0)

        for col in ("threat_class", "event_type", "severity", "source", "explain_method"):
            df[col] = None
        df["risk_score"] = 0.0
        df["explanation"] = [[] for _ in range(len(df))]

        idx = df.index[df["flagged"]]
        if len(idx):
            expl, method = self.detector.explain(X.loc[idx])
            for i, e in zip(idx, expl):
                row = df.loc[i]
                cls = classify(row["rule_hits"], [x["feature"] for x in e])
                rule_hit = len(row["rule_hits"]) > 0
                risk = risk_score(row["anomaly_score"], rule_hit, cls, PROFILES[row["device_type"]].criticality)
                df.at[i, "threat_class"] = cls
                df.at[i, "event_type"] = EVENT_TYPES[cls]
                df.at[i, "risk_score"] = risk
                df.at[i, "severity"] = severity(risk)
                df.at[i, "source"] = "ids+ml" if rule_hit and row["ml_flag"] else ("ids" if rule_hit else "ml")
                df.at[i, "explanation"] = e
                df.at[i, "explain_method"] = method
        return df
