"""Rule-based IDS. Each rule is a vectorised predicate over the preprocessed frame."""
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    threat_class: str
    priority: int  # higher wins when several rules fire on one row
    predicate: Callable[[pd.DataFrame], pd.Series]


RULES = [
    Rule("R-TEMP-HIGH", "Temperature > 6 sigma above nominal", "thermal_anomaly", 1,
         lambda d: d["z_temperature"] >= 6),
    Rule("R-NET-SPIKE", "Inbound packet rate >= 3x nominal", "network_anomaly", 2,
         lambda d: d["net_in_pps"] >= 3 * d["mean_net_in_pps"]),
    Rule("R-LOGIN-BURST", ">= 5 failed logins in one sample", "unauthorized_access", 3,
         lambda d: d["failed_logins"] >= 5),
    Rule("R-TELEMETRY-FLATLINE", "Temperature and pressure frozen over full window", "telemetry_manipulation", 4,
         lambda d: (d["rstd_temperature"] < 0.15) & (d["rstd_pressure"] < 0.15)),
]
RULE_BY_ID = {r.id: r for r in RULES}


def evaluate(df: pd.DataFrame) -> pd.DataFrame:
    """Boolean DataFrame (same index as df), one column per rule id."""
    return pd.DataFrame({r.id: r.predicate(df).fillna(False) for r in RULES}, index=df.index)
