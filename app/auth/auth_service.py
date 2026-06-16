from sqlalchemy.orm import Session

from app.auth import otp_provider
from app.auth.session_manager import create_session
from app.consent.consent_service import record_consent_acceptance
from app.models.user import User


class RegistrationError(ValueError):
    pass


DASHBOARD_ROUTES = {
    "provider": "/dashboards/mantrana",
    "patient": "/dashboards/rogi",
    "caregiver": "/dashboards/sahay",
}


def _ensure_mobile_verified(mobile_number: str):
    if not otp_provider.is_mobile_verified(mobile_number):
        raise RegistrationError("OTP verification is required before registration")


def _ensure_unique_mobile(db: Session, mobile_number: str):
    existing = db.query(User).filter(User.mobile_number == mobile_number).first()
    if existing is not None:
        raise RegistrationError("A user with this mobile number already exists")


def _ensure_terms_accepted(terms_accepted: bool):
    if terms_accepted is not True:
        raise RegistrationError("Terms acceptance is required")


def _registration_response(user: User, session, consent=None):
    response = {
        "user": user,
        "session": session,
        "dashboard_route": DASHBOARD_ROUTES[user.role],
    }
    if consent is not None:
        response["consent"] = consent
    return response


def register_provider(db: Session, registration):
    _ensure_mobile_verified(registration.mobile_number)
    _ensure_unique_mobile(db, registration.mobile_number)
    _ensure_terms_accepted(registration.terms_accepted)

    user = User(
        role="provider",
        full_name=registration.full_name,
        mobile_number=registration.mobile_number,
        email_address=registration.email_address,
        professional_category=registration.professional_category,
        registration_number=registration.registration_number,
        hpid_number=registration.hpid_number,
        terms_accepted=registration.terms_accepted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = create_session(db, user)
    otp_provider.consume_mobile_verification(registration.mobile_number)
    return _registration_response(user, session)


def register_patient(db: Session, registration, ip_address: str = None):
    _ensure_mobile_verified(registration.mobile_number)
    _ensure_unique_mobile(db, registration.mobile_number)
    _ensure_terms_accepted(registration.terms_accepted)
    if registration.unified_consent_accepted is not True:
        raise RegistrationError("Unified consent acceptance is required for patient registration")

    user = User(
        role="patient",
        full_name=registration.full_name,
        mobile_number=registration.mobile_number,
        date_of_birth=registration.date_of_birth,
        gender=registration.gender,
        preferred_language=registration.preferred_language,
        abha_number=registration.abha_number,
        emergency_contact_name=registration.emergency_contact_name,
        emergency_contact_mobile=registration.emergency_contact_mobile,
        terms_accepted=registration.terms_accepted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    consent = record_consent_acceptance(db, patient_id=user.id, ip_address=ip_address)
    session = create_session(db, user)
    otp_provider.consume_mobile_verification(registration.mobile_number)
    return _registration_response(user, session, consent=consent)


def register_caregiver(db: Session, registration):
    _ensure_mobile_verified(registration.mobile_number)
    _ensure_unique_mobile(db, registration.mobile_number)
    _ensure_terms_accepted(registration.terms_accepted)

    user = User(
        role="caregiver",
        full_name=registration.full_name,
        mobile_number=registration.mobile_number,
        relationship_to_patient=registration.relationship_to_patient,
        preferred_language=registration.preferred_language,
        terms_accepted=registration.terms_accepted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = create_session(db, user)
    otp_provider.consume_mobile_verification(registration.mobile_number)
    return _registration_response(user, session)


def login(db: Session, mobile_number: str):
    if not otp_provider.is_mobile_verified(mobile_number):
        raise RegistrationError("OTP verification is required before login")

    user = db.query(User).filter(User.mobile_number == mobile_number, User.is_active.is_(True)).first()
    if user is None:
        raise RegistrationError("No active user exists for this mobile number")

    session = create_session(db, user)
    otp_provider.consume_mobile_verification(mobile_number)
    return _registration_response(user, session)
