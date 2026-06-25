from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CareTask(Base):
    __tablename__ = "care_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type in ('medication', 'measurement', 'recommendation', 'investigation')",
            name="ck_care_tasks_type",
        ),
        CheckConstraint(
            "execution_status in ('pending', 'completed', 'completed_late', 'missed')",
            name="ck_care_tasks_execution_status",
        ),
        CheckConstraint("ordinal > 0", name="ck_care_tasks_ordinal"),
        UniqueConstraint("advisory_id", "ordinal", name="uq_care_task_advisory_ordinal"),
        Index("idx_care_tasks_patient_status_due", "patient_id", "execution_status", "due_at"),
        Index("idx_care_tasks_provider_status_due", "provider_id", "execution_status", "due_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_uid = Column(String(64), nullable=False, unique=True, index=True)
    advisory_id = Column(Integer, ForeignKey("advisories.id"), nullable=False, index=True)
    care_plan_id = Column(Integer, ForeignKey("care_plans.id"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String(32), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    expected_response = Column(String(32), nullable=False)
    ordinal = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    grace_expires_at = Column(DateTime, nullable=False, index=True)
    execution_status = Column(String(32), nullable=False, default="pending", index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    advisory = relationship("Advisory", back_populates="tasks")
    care_plan = relationship("CarePlan")
    provider = relationship("User", foreign_keys=[provider_id])
    patient = relationship("User", foreign_keys=[patient_id])
    response = relationship("TaskResponse", back_populates="task", uselist=False)
    attachment = relationship("ClinicalAttachment", back_populates="task", uselist=False)


class TaskResponse(Base):
    __tablename__ = "task_responses"
    __table_args__ = (
        CheckConstraint(
            "response_status in ('taken', 'missed', 'done', 'recorded', 'uploaded')",
            name="ck_task_responses_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    response_uid = Column(String(64), nullable=False, unique=True, index=True)
    task_id = Column(Integer, ForeignKey("care_tasks.id"), nullable=False, unique=True, index=True)
    advisory_id = Column(Integer, ForeignKey("advisories.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    response_status = Column(String(32), nullable=False, index=True)
    response_value_json = Column(Text, nullable=False)
    is_late = Column(Boolean, nullable=False, default=False)
    response_event_id = Column(String(64), nullable=True, unique=True, index=True)
    responded_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    task = relationship("CareTask", back_populates="response")
    attachment = relationship("ClinicalAttachment", back_populates="response", uselist=False)


class ClinicalAttachment(Base):
    __tablename__ = "clinical_attachments"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_clinical_attachments_size"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attachment_uid = Column(String(64), nullable=False, unique=True, index=True)
    task_id = Column(Integer, ForeignKey("care_tasks.id"), nullable=False, unique=True, index=True)
    response_id = Column(Integer, ForeignKey("task_responses.id"), nullable=True, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(180), nullable=False)
    content_type = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    storage_path = Column(String(500), nullable=False, unique=True)
    uploaded_at = Column(DateTime, nullable=False)

    task = relationship("CareTask", back_populates="attachment")
    response = relationship("TaskResponse", back_populates="attachment")


class ClinicalAlert(Base):
    __tablename__ = "clinical_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type in ('allergy_conflict', 'non_response', 'value_threshold')",
            name="ck_clinical_alerts_type",
        ),
        CheckConstraint(
            "severity in ('low', 'medium', 'high', 'critical')",
            name="ck_clinical_alerts_severity",
        ),
        CheckConstraint(
            "status in ('NEW', 'ACKNOWLEDGED', 'RESOLVED')",
            name="ck_clinical_alerts_status",
        ),
        CheckConstraint(
            "notification_mode in ('immediate', 'daily_summary', 'both')",
            name="ck_clinical_alerts_notification_mode",
        ),
        Index("idx_clinical_alerts_provider_status_created", "provider_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    alert_uid = Column(String(64), nullable=False, unique=True, index=True)
    advisory_id = Column(Integer, ForeignKey("advisories.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("care_tasks.id"), nullable=True, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_type = Column(String(32), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    message = Column(String(500), nullable=False)
    notification_mode = Column(String(32), nullable=False, default="immediate")
    status = Column(String(20), nullable=False, default="NEW", index=True)
    event_id = Column(String(64), nullable=True, unique=True, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    advisory = relationship("Advisory")
    task = relationship("CareTask")
    provider = relationship("User", foreign_keys=[provider_id])
    patient = relationship("User", foreign_keys=[patient_id])
