"""Cleaning + feature engineering. Pure functions (no DB)."""
import numpy as np
import pandas as pd

from app.simulator.profiles import CHANNELS, PROFILES

WINDOW = 8  # samples used for rolling statistics
Z_CLIP = 25.0
FEATURES = [
    "z_temperature", "z_pressure", "z_vibration", "z_cpu_load",
    "z_net_in_pps", "z_net_out_pps", "z_failed_logins", "z_cmd_rate",
    "d_temperature", "d_pressure",        # sample-to-sample change (in sigmas)
    "rstd_temperature", "rstd_pressure",  # rolling std / expected std (~1 normally, ~0 when frozen)
]


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Expects columns: device_pk, device_type, ts + raw channels. Returns a sorted copy with features."""
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values(["device_pk", "ts"], kind="stable").reset_index(drop=True)

    mean = {c: df["device_type"].map(lambda t, c=c: PROFILES[t].baselines[c][0]).astype(float) for c in CHANNELS}
    std = {c: df["device_type"].map(lambda t, c=c: PROFILES[t].baselines[c][1]).astype(float) for c in CHANNELS}
    g = df.groupby("device_pk")

    for c in CHANNELS:  # cleaning: coerce, forward-fill per device, fall back to the type's nominal mean
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df.groupby("device_pk")[c].ffill().fillna(mean[c])
        df[f"z_{c}"] = ((df[c] - mean[c]) / std[c]).clip(-Z_CLIP, Z_CLIP)
        df[f"mean_{c}"] = mean[c]

    for c in ("temperature", "pressure"):
        df[f"d_{c}"] = (g[c].diff() / std[c]).fillna(0.0).clip(-Z_CLIP, Z_CLIP)
        roll = df.groupby("device_pk")[c].transform(lambda s: s.rolling(WINDOW, min_periods=WINDOW).std())
        df[f"rstd_{c}"] = (roll / std[c]).clip(0, 10)  # NaN until the window is full
    return df


def feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURES].fillna(1.0).astype(float)  # incomplete window -> "normal" variability
