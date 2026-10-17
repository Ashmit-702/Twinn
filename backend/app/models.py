from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. CNC-MA-941
    device_type: Mapped[str] = mapped_column(String(32))
    facility: Mapped[str] = mapped_column(String(64))
    ip_address: Mapped[str] = mapped_column(String(45))
    is_online: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DigitalTwin(Base):
    __tablename__ = "digital_twins"
    id: Mapped[int] = mapped_column(primary_key=True)
    twin_code: Mapped[str] = mapped_column(String(16), unique=True)
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="Healthy")
    security_score: Mapped[float] = mapped_column(Float, default=100.0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Telemetry(Base):
    __tablename__ = "telemetry"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    temperature: Mapped[float] = mapped_column(Float)
    pressure: Mapped[float] = mapped_column(Float)
    vibration: Mapped[float] = mapped_column(Float)
    cpu_load: Mapped[float] = mapped_column(Float)
    net_in_pps: Mapped[float] = mapped_column(Float)
    net_out_pps: Mapped[float] = mapped_column(Float)
    failed_logins: Mapped[float] = mapped_column(Float)
    cmd_rate: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Simulator ground truth. Used ONLY for evaluation / baseline selection, never as a detection input.
    scenario: Mapped[str | None] = mapped_column(String(32), nullable=True)
    __table_args__ = (Index("ix_telemetry_device_ts", "device_pk", "ts"), Index("ix_telemetry_ts", "ts"))


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    threat_class: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))  # Low | Medium | High | Critical
    source: Mapped[str] = mapped_column(String(16))  # ids | ml | ids+ml
    anomaly_score: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    rule_ids: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    threat_class: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open | resolved
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=1)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    scenario: Mapped[str] = mapped_column(String(32))
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    total_ticks: Mapped[int] = mapped_column(Integer)
    ticks_done: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | finished
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
