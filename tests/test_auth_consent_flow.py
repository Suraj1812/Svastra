from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import auth_service, otp_provider
from app.auth.session_manager import logout, validate_session
from app.consent.consent_service import get_patient_consent_status
from app.database import Base
from app.models import consent, session, user  # noqa: F401
from app.reference_terms import decode_reference_term, get_reference_term
from app.schemas.registration import (
    CaregiverRegistration,
    PatientRegistration,
    ProviderRegistration,
)


GENDER_FEMALE = get_reference_term("gender", "Female")
LANGUAGE_ENGLISH = get_reference_term("language", "English")
LANGUAGE_HINDI = get_reference_term("language", "Hindi")
OCCUPATION_PHYSICIAN = get_reference_term("occupation", "Physician")
RELATIONSHIP_FAMILY = get_reference_term("relationship", "Family member")


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


def _verify_mobile(mobile_number):
    otp_provider.send_otp(mobile_number)
    assert otp_provider.verify_otp(mobile_number, "123456") is True


def test_patient_registration_requires_and_records_unified_consent(db_session):
    with pytest.raises(ValidationError):
        PatientRegistration(
            full_name="Asha Patient",
            mobile_number="9876543210",
            date_of_birth=date(1992, 5, 17),
            gender=GENDER_FEMALE,
            preferred_language=LANGUAGE_ENGLISH,
            terms_accepted=True,
            unified_consent_accepted=False,
        )

    _verify_mobile("9876543210")
    result = auth_service.register_patient(
        db_session,
        PatientRegistration(
            full_name="Asha Patient",
            mobile_number="9876543210",
            date_of_birth=date(1992, 5, 17),
            gender=GENDER_FEMALE,
            preferred_language=LANGUAGE_ENGLISH,
            terms_accepted=True,
            unified_consent_accepted=True,
        ),
        ip_address="127.0.0.1",
    )

    assert result["user"].role == "patient"
    assert decode_reference_term(result["user"].gender, "gender") == GENDER_FEMALE
    assert result["dashboard_route"] == "/dashboards/rogi"
    assert result["consent"].patient_id == result["user"].id
    assert result["consent"].ip_address == "127.0.0.1"

    consent_status = get_patient_consent_status(db_session, result["user"].id)
    assert consent_status["accepted"] is True
    assert validate_session(db_session, result["session"].session_token) is not None


def test_provider_and_caregiver_registration_create_sessions(db_session):
    _verify_mobile("9876543211")
    provider_result = auth_service.register_provider(
        db_session,
        ProviderRegistration(
            full_name="Dr Meera",
            mobile_number="9876543211",
            professional_category=OCCUPATION_PHYSICIAN,
            registration_number="REG-123",
            terms_accepted=True,
        ),
    )

    assert provider_result["user"].role == "provider"
    assert provider_result["dashboard_route"] == "/dashboards/mantrana"
    assert validate_session(db_session, provider_result["session"].session_token) is not None

    _verify_mobile("9876543212")
    caregiver_result = auth_service.register_caregiver(
        db_session,
        CaregiverRegistration(
            full_name="Ravi Caregiver",
            mobile_number="9876543212",
            relationship_to_patient=RELATIONSHIP_FAMILY,
            preferred_language=LANGUAGE_HINDI,
            terms_accepted=True,
        ),
    )

    assert caregiver_result["user"].role == "caregiver"
    assert caregiver_result["dashboard_route"] == "/dashboards/sahay"
    assert validate_session(db_session, caregiver_result["session"].session_token) is not None


def test_login_requires_fresh_otp_and_logout_invalidates_session(db_session):
    _verify_mobile("9876543213")
    auth_service.register_provider(
        db_session,
        ProviderRegistration(
            full_name="Dr Arjun",
            mobile_number="9876543213",
            professional_category=OCCUPATION_PHYSICIAN,
            registration_number="REG-456",
            terms_accepted=True,
        ),
    )

    with pytest.raises(auth_service.RegistrationError):
        auth_service.login(db_session, "9876543213")

    _verify_mobile("9876543213")
    login_result = auth_service.login(db_session, "9876543213")
    token = login_result["session"].session_token

    assert validate_session(db_session, token) is not None
    assert logout(db_session, token) is True
    assert validate_session(db_session, token) is None
