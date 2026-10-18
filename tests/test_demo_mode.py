import time

from sqlalchemy import func, select

from backend import demo
from backend.models import Device, SecurityEvent
from sqlalchemy.orm import Session


def _snapshot(engine):
    with Session(engine) as s:
        return (sorted(s.scalars(select(Device.device_id))), s.scalar(select(func.count(SecurityEvent.id))),
                sorted((e.event_type, e.severity) for e in s.scalars(select(SecurityEvent))))


def test_demo_data_is_deterministic_for_a_time_bucket(monkeypatch):
    """Different serverless instances in the same 10-minute bucket must show the same factory."""
    bucket = int(time.time() // demo.BUCKET_SECONDS)
    a = _snapshot(demo._build(bucket))
    b = _snapshot(demo._build(bucket))
    assert a == b and a[1] > 0 and len(a[0]) == 24


def test_demo_engine_is_cached_per_bucket():
    demo.reset_for_tests()
    assert demo.demo_engine() is demo.demo_engine()
