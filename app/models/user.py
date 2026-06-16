from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('provider', 'patient', 'caregiver', 'admin')", name="ck_users_role"),
        CheckConstraint("terms_accepted = 1", name="ck_users_terms_accepted"),
        CheckConstraint(
            "role != 'provider' or (professional_category is not null and registration_number is not null)",
            name="ck_provider_required_fields",
        ),
        CheckConstraint(
            "role != 'patient' or (date_of_birth is not null and gender is not null and preferred_language is not null)",
            name="ck_patient_required_fields",
        ),
        CheckConstraint(
            "role != 'caregiver' or (relationship_to_patient is not null and preferred_language is not null)",
            name="ck_caregiver_required_fields",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(32), nullable=False, index=True)

    full_name = Column(String(255), nullable=False)
    mobile_number = Column(String(32), nullable=False, unique=True, index=True)
    email_address = Column(String(255), nullable=True)

    professional_category = Column(String(100), nullable=True)
    registration_number = Column(String(100), nullable=True)
    hpid_number = Column(String(100), nullable=True)

    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(64), nullable=True)
    preferred_language = Column(String(64), nullable=True)
    abha_number = Column(String(100), nullable=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_mobile = Column(String(32), nullable=True)

    relationship_to_patient = Column(String(100), nullable=True)
    terms_accepted = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    consent_acceptances = relationship(
        "ConsentAcceptance",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    platform_consents = relationship(
        "PlatformConsent",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
