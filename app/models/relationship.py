from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ProviderPatientLink(Base):
    __tablename__ = "provider_patient_links"
    __table_args__ = (
        CheckConstraint("status in ('active', 'ended')", name="ck_provider_patient_link_status"),
        CheckConstraint("provider_id <> patient_id", name="ck_provider_patient_distinct"),
    )

    link_id = Column(String(64), primary_key=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_consent_id = Column(
        Integer,
        ForeignKey("relationship_consents.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)

    provider = relationship("User", foreign_keys=[provider_id])
    patient = relationship("User", foreign_keys=[patient_id])
    source_consent = relationship("RelationshipConsent")


class PatientCaregiverLink(Base):
    __tablename__ = "patient_caregiver_links"
    __table_args__ = (
        CheckConstraint("status in ('active', 'ended')", name="ck_patient_caregiver_link_status"),
        CheckConstraint("patient_id <> caregiver_id", name="ck_patient_caregiver_distinct"),
    )

    link_id = Column(String(64), primary_key=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_consent_id = Column(
        Integer,
        ForeignKey("relationship_consents.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    relationship_type = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)

    patient = relationship("User", foreign_keys=[patient_id])
    caregiver = relationship("User", foreign_keys=[caregiver_id])
    source_consent = relationship("RelationshipConsent")
