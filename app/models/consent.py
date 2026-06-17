from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ConsentVersion(Base):
    __tablename__ = "consent_versions"

    consent_version = Column(String(100), primary_key=True)
    title = Column(String(255), nullable=False)
    markdown_file = Column(String(255), nullable=False)
    effective_from = Column(DateTime, nullable=False, server_default=func.now())
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class PlatformConsent(Base):
    __tablename__ = "platform_consents"
    __table_args__ = (
        UniqueConstraint("patient_id", "consent_version", name="uq_patient_platform_consent_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consent_version = Column(String(100), nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=False, server_default=func.now())
    application_name = Column(String(100), nullable=False)
    app_version = Column(String(50), nullable=False)
    ip_address = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    patient = relationship("User", back_populates="platform_consents")


class RelationshipConsent(Base):
    __tablename__ = "relationship_consents"
    __table_args__ = (
        CheckConstraint(
            "consent_type in ('provider_access', 'caregiver_access')",
            name="ck_relationship_consents_type",
        ),
        CheckConstraint(
            "status in ('PENDING', 'ACTIVE', 'REJECTED', 'REVOKED', 'EXPIRED')",
            name="ck_relationship_consents_status",
        ),
        CheckConstraint("length(alias) <= 60", name="ck_relationship_consents_alias_length"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requestor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requestor_role = Column(String(32), nullable=False, index=True)
    consent_type = Column(String(64), nullable=False, index=True)
    alias = Column(String(60), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    granted_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    patient = relationship("User", foreign_keys=[patient_id], back_populates="patient_consents")
    requestor = relationship("User", foreign_keys=[requestor_id], back_populates="requested_consents")


class ConsentCEPEvent(Base):
    __tablename__ = "consent_cep_events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(100), nullable=False, index=True)
    consent_id = Column(Integer, ForeignKey("relationship_consents.id"), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    consent = relationship("RelationshipConsent")


class ConsentAcceptance(Base):
    __tablename__ = "consent_acceptances"
    __table_args__ = (
        UniqueConstraint("patient_id", "consent_version", name="uq_patient_consent_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consent_version = Column(String(100), nullable=False, index=True)
    accepted_at = Column(DateTime, nullable=False, server_default=func.now())
    application_name = Column(String(100), nullable=False)
    app_version = Column(String(50), nullable=False)
    ip_address = Column(String(64), nullable=True)

    patient = relationship("User", back_populates="consent_acceptances")
