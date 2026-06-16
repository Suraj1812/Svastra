from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
