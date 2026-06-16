from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import otp_provider
from app.config import settings
from app.models.consent import ConsentVersion, PlatformConsent
from app.models.user import User


SUPPORTED_RELATIONSHIP_CONSENT_TYPES = ("provider_access", "caregiver_access")
SUPPORTED_RELATIONSHIP_STATES = ("PENDING", "GRANTED", "REJECTED", "REVOKED", "EXPIRED")


def _ensure_default_consent_version(db: Session):
    existing = (
        db.query(ConsentVersion)
        .filter(ConsentVersion.consent_version == settings.consent_version)
        .first()
    )
    if existing is not None:
        return existing

    consent_version = ConsentVersion(
        consent_version=settings.consent_version,
        title="Svastra+ Unified Platform Consent",
        markdown_file=settings.consent_document_path.name,
        effective_from=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(consent_version)
    db.commit()
    db.refresh(consent_version)
    return consent_version


def get_current_consent_version(db: Session = None):
    if db is None:
        return settings.consent_version

    current = db.query(ConsentVersion).filter(ConsentVersion.is_current.is_(True)).first()
    if current is not None:
        return current.consent_version

    return _ensure_default_consent_version(db).consent_version


def get_current_consent_document():
    if not settings.consent_document_path.exists():
        return ""

    return settings.consent_document_path.read_text(encoding="utf-8-sig")


def record_consent_acceptance(
    db: Session,
    patient_id: int,
    application_name: str = None,
    app_version: str = None,
    ip_address: str = None,
    consent_version: str = None,
):
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if patient is None:
        raise ValueError("Consent can only be recorded for a registered patient")

    version = consent_version or get_current_consent_version(db)
    existing = (
        db.query(PlatformConsent)
        .filter(
            PlatformConsent.patient_id == patient_id,
            PlatformConsent.consent_version == version,
            PlatformConsent.is_active.is_(True),
        )
        .first()
    )
    if existing is not None:
        return existing

    consent = PlatformConsent(
        patient_id=patient_id,
        consent_version=version,
        application_name=application_name or settings.app_name,
        app_version=app_version or settings.app_version,
        ip_address=ip_address,
        is_active=True,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def get_patient_consent_status(db: Session, patient_id: int):
    current_version = get_current_consent_version(db)
    acceptance = (
        db.query(PlatformConsent)
        .filter(
            PlatformConsent.patient_id == patient_id,
            PlatformConsent.consent_version == current_version,
            PlatformConsent.is_active.is_(True),
        )
        .first()
    )

    return {
        "patient_id": patient_id,
        "current_consent_version": current_version,
        "consent_version": acceptance.consent_version if acceptance is not None else current_version,
        "accepted": acceptance is not None,
        "accepted_at": acceptance.accepted_at if acceptance is not None else None,
        "consent_status": "Accepted" if acceptance is not None else "Pending",
        "application_name": acceptance.application_name if acceptance is not None else None,
        "app_version": acceptance.app_version if acceptance is not None else None,
    }


def validate_consent_request(consent_type: str, status_value: str = "PENDING"):
    if consent_type not in SUPPORTED_RELATIONSHIP_CONSENT_TYPES:
        raise ValueError("Unsupported consent type")
    if status_value not in SUPPORTED_RELATIONSHIP_STATES:
        raise ValueError("Unsupported consent request status")
    return True


def create_consent_request(*_, consent_type: str, **__):
    validate_consent_request(consent_type)
    return {
        "id": None,
        "consent_type": consent_type,
        "status": "PENDING",
        "implementation_status": "stubbed_for_wednesday",
    }


def get_pending_consent_requests(*_, **__):
    return []


def _validate_relationship_decision_otp(otp: str):
    if otp != otp_provider.MOCK_OTP:
        raise ValueError("OTP verification is required before consent decision")
    return True


def grant_consent_request(*_, request_id: str, otp: str, **__):
    _validate_relationship_decision_otp(otp)
    return {
        "request_id": request_id,
        "status": "GRANTED",
        "implementation_status": "placeholder_for_wednesday",
    }


def reject_consent_request(*_, request_id: str, otp: str, **__):
    _validate_relationship_decision_otp(otp)
    return {
        "request_id": request_id,
        "status": "REJECTED",
        "implementation_status": "placeholder_for_wednesday",
    }
