from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        Index("idx_timeline_patient_occurred_id", "patient_id", "occurred_at", "id"),
        Index("idx_timeline_patient_type_occurred", "patient_id", "event_type", "occurred_at"),
        Index("idx_timeline_patient_related_occurred", "patient_id", "related_user_id", "occurred_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    related_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_app = Column(String(64), nullable=False)
    target_app = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    payload_sha256 = Column(String(64), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])


class OutboundEvent(Base):
    __tablename__ = "outbound_events"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'sent', 'acknowledged', 'failed')",
            name="ck_outbound_events_status",
        ),
        CheckConstraint("retry_count >= 0", name="ck_outbound_events_retry_count"),
        Index("idx_outbound_patient_status_created", "patient_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_app = Column(String(64), nullable=False, index=True)
    cep_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    last_attempt_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    last_error_code = Column(String(64), nullable=True)
    last_error_message = Column(String(255), nullable=True)

    patient = relationship("User")


class ReceivedEvent(Base):
    __tablename__ = "received_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    target_app = Column(String(64), nullable=False, index=True)
    cep_json = Column(Text, nullable=False)
    received_at = Column(DateTime, nullable=False, server_default=func.now())


class PostOfficeAcknowledgement(Base):
    __tablename__ = "postoffice_acknowledgements"

    id = Column(Integer, primary_key=True, index=True)
    ack_id = Column(String(64), nullable=False, unique=True, index=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    received_by = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
