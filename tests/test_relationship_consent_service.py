from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import otp_provider
from app.consent.consent_service import create_consent_request, grant_consent, revoke_consent
from app.consent.consent_validator import ConsentAccessDenied, has_provider_access, validate_access
from app.database import Base
from app.models import audit, consent, rbac, session, user  # noqa: F401
from app.models.audit import AuditLog
from app.models.consent import ConsentCEPEvent
from app.models.user import User
from app.reference_terms import encode_reference_term, get_reference_term


GENDER_FEMALE = get_reference_term("gender", "Female")
LANGUAGE_ENGLISH = get_reference_term("language", "English")
OCCUPATION_PHYSICIAN = get_reference_term("occupation", "Physician")


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    otp_provider.reset_verifications()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        otp_provider.reset_verifications()


def _seed_patient_and_provider(db):
    patient = User(
        role="patient",
        full_name="Asha Patient",
        mobile_number="9876500001",
        date_of_birth=date(1992, 5, 17),
        gender=encode_reference_term(GENDER_FEMALE),
        preferred_language=encode_reference_term(LANGUAGE_ENGLISH),
        terms_accepted=True,
    )
    provider = User(
        role="provider",
        full_name="Dr Meera",
        mobile_number="9876500002",
        professional_category=encode_reference_term(OCCUPATION_PHYSICIAN),
        registration_number="REG-123",
        terms_accepted=True,
    )
    db.add_all([patient, provider])
    db.commit()
    db.refresh(patient)
    db.refresh(provider)
    return patient, provider


def test_relationship_consent_service_records_audit_cep_and_enforces_access(db_session):
    patient, provider = _seed_patient_and_provider(db_session)

    consent = create_consent_request(
        db_session,
        patient_id=patient.id,
        requestor_user=provider,
        consent_type="provider_access",
    )

    assert consent.status == "PENDING"
    assert has_provider_access(db_session, provider_id=provider.id, patient_id=patient.id) is False
    with pytest.raises(ConsentAccessDenied):
        validate_access(
            db_session,
            patient_id=patient.id,
            requestor_id=provider.id,
            consent_type="provider_access",
        )

    granted = grant_consent(
        db_session,
        consent_id=consent.id,
        actor_user=patient,
        otp="123456",
    )

    assert granted.status == "ACTIVE"
    assert has_provider_access(db_session, provider_id=provider.id, patient_id=patient.id) is True
    assert (
        validate_access(
            db_session,
            patient_id=patient.id,
            requestor_id=provider.id,
            consent_type="provider_access",
        ).id
        == consent.id
    )

    revoked = revoke_consent(
        db_session,
        consent_id=consent.id,
        actor_user=patient,
        otp="123456",
    )

    assert revoked.status == "REVOKED"
    assert has_provider_access(db_session, provider_id=provider.id, patient_id=patient.id) is False
    assert db_session.query(AuditLog).filter(AuditLog.action == "consent.request").count() == 1
    assert db_session.query(AuditLog).filter(AuditLog.action == "consent.grant").count() == 1
    assert db_session.query(AuditLog).filter(AuditLog.action == "consent.revoke").count() == 1
    assert db_session.query(ConsentCEPEvent).filter(ConsentCEPEvent.event_name == "consent.request").count() == 1
    assert db_session.query(ConsentCEPEvent).filter(ConsentCEPEvent.event_name == "consent.grant").count() == 1
    assert db_session.query(ConsentCEPEvent).filter(ConsentCEPEvent.event_name == "consent.revoke").count() == 1
