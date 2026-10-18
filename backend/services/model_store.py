"""The trained detector is persisted in PostgreSQL (table model_artifacts) and cached per warm instance.

Every request compares the latest artifact id with its cache, so a re-seed on one instance is picked up by
the others. If no artifact exists (or the table was cleared) it is retrained from clean baseline telemetry.
"""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import Device, ModelArtifact, Telemetry
from backend.security.anomaly import AnomalyDetector
from backend.security.pipeline import SecurityPipeline
from backend.security.preprocessing import feature_matrix, preprocess
from backend.simulator.profiles import CHANNELS

_cache: tuple[int, AnomalyDetector] | None = None


class ModelNotReady(RuntimeError):
    pass


def clear_cache() -> None:
    global _cache
    _cache = None


def _latest_id(session: Session) -> int | None:
    return session.scalar(select(ModelArtifact.id).order_by(ModelArtifact.id.desc()).limit(1))


def model_ready(session: Session) -> bool:
    return _latest_id(session) is not None


def set_detector(session: Session, detector: AnomalyDetector, meta: dict | None = None) -> None:
    """Replace the stored model (caller commits). Keeps only the newest artifact."""
    global _cache
    session.execute(delete(ModelArtifact))
    art = ModelArtifact(created_at=datetime.now(timezone.utc), payload=detector.to_bytes(), meta=meta or {})
    session.add(art)
    session.flush()
    _cache = (art.id, detector)


def get_pipeline(session: Session) -> SecurityPipeline:
    global _cache
    latest = _latest_id(session)
    if latest is None:
        return SecurityPipeline(train_from_db(session))
    if _cache is None or _cache[0] != latest:
        art = session.get(ModelArtifact, latest)
        _cache = (latest, AnomalyDetector.from_bytes(art.payload))
    return SecurityPipeline(_cache[1])


def train_from_db(session: Session, limit: int = 30000) -> AnomalyDetector:
    """Train on rows recorded during known-clean operation (no injected scenario)."""
    cols = [Telemetry.device_pk, Telemetry.ts, *[getattr(Telemetry, c) for c in CHANNELS], Device.device_type]
    q = (select(*cols).join(Device, Device.id == Telemetry.device_pk)
         .where(Telemetry.scenario.is_(None)).order_by(Telemetry.ts).limit(limit))
    df = pd.DataFrame(session.execute(q).mappings().all())
    if len(df) < 500:
        raise ModelNotReady("Not enough clean baseline telemetry to train. Initialise the simulation first.")
    det = AnomalyDetector().fit(feature_matrix(preprocess(df)))
    set_detector(session, det, {"trained_on": "db_clean_baseline", "rows": len(df)})
    return det
