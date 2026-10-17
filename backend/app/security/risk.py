"""Risk assessment: combine ML score, rule evidence, threat type and device criticality."""
THREAT_WEIGHT = {
    "telemetry_manipulation": 0.95, "unauthorized_access": 0.90, "thermal_anomaly": 0.80,
    "network_anomaly": 0.70, "unclassified_anomaly": 0.50,
}


def risk_score(anomaly_score: float, rule_hit: bool, threat_class: str, criticality: float) -> float:
    """0-100. 0.30*ML + 0.30*threat weight + 0.20*device criticality + 0.20*rule evidence."""
    r = 0.30 * anomaly_score / 100 + 0.30 * THREAT_WEIGHT.get(threat_class, 0.5) \
        + 0.20 * criticality + 0.20 * (1.0 if rule_hit else 0.0)
    return round(100 * min(1.0, r), 1)


def severity(risk: float) -> str:
    if risk >= 78:
        return "Critical"
    if risk >= 68:
        return "High"
    if risk >= 45:
        return "Medium"
    return "Low"
