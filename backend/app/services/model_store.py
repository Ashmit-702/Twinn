"""Holds the trained detector (in memory + on disk) and can retrain from stored clean baseline data."""
import threading

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Device, Telemetry
from app.security.anomaly import AnomalyDetector
from app.security.pipeline import SecurityPipeline
from app.security.preprocessing import feature_matrix, preprocess
from app.simulator.profiles import CHANNELS

_lock = threading.Lock()
_detector: AnomalyDetector | None = None


class ModelNotReady(RuntimeError):
    pass


def set_detector(d: AnomalyDetector | None, persist: bool = True) -> None:
    global _detector
    with _lock:
        _detector = d
        if d is not None and persist:
            d.save(get_settings().model_dir)


def model_ready() -> bool:
    return _detector is not None or AnomalyDetector.load(get_settings().model_dir) is not None


def get_pipeline(session: Session) -> SecurityPipeline:
    global _detector
    with _lock:
        if _detector is None:
            _detector = AnomalyDetector.load(get_settings().model_dir)
    if _detector is None:  # e.g. ephemeral disk after redeploy: retrain from stored baseline
        train_from_db(session)
    return SecurityPipeline(_detector)


def train_from_db(session: Session, limit: int = 30000) -> AnomalyDetector:
    """Train on rows recorded during known-clean operation (no injected scenario)."""
    cols = [Telemetry.device_pk, Telemetry.ts, *[getattr(Telemetry, c) for c in CHANNELS], Device.device_type]
    q = (select(*cols).join(Device, Device.id == Telemetry.device_pk)
         .where(Telemetry.scenario.is_(None)).order_by(Telemetry.ts).limit(limit))
    df = pd.DataFrame(session.execute(q).mappings().all())
    if len(df) < 500:
        raise ModelNotReady("Not enough clean baseline telemetry to train. Run the simulator seed first.")
    det = AnomalyDetector().fit(feature_matrix(preprocess(df)))
    set_detector(det)
    return det
