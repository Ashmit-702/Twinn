"""Threat classification: IDS rules first, then SHAP top-feature mapping for ML-only detections."""
from app.security.ids import RULE_BY_ID

EVENT_TYPES = {
    "thermal_anomaly": "Abnormal Temperature",
    "unauthorized_access": "Unauthorized Access Attempt",
    "network_anomaly": "Anomalous TCP/UDP Activity",
    "telemetry_manipulation": "Telemetry Manipulation Suspected",
    "unclassified_anomaly": "Unclassified Anomaly",
}
FEATURE_CLASS = {
    "z_temperature": "thermal_anomaly", "d_temperature": "thermal_anomaly",
    "z_failed_logins": "unauthorized_access", "z_cmd_rate": "unauthorized_access",
    "z_net_in_pps": "network_anomaly", "z_net_out_pps": "network_anomaly",
    "rstd_temperature": "telemetry_manipulation", "rstd_pressure": "telemetry_manipulation",
}


def classify(rule_ids: list[str], top_features: list[str]) -> str:
    if rule_ids:
        best = max((RULE_BY_ID[r] for r in rule_ids), key=lambda r: r.priority)
        return best.threat_class
    for f in top_features[:1]:  # ML-only: trust the single strongest contributing feature
        if f in FEATURE_CLASS:
            return FEATURE_CLASS[f]
    return "unclassified_anomaly"
