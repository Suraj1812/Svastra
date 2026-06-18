from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.consent.consent_audit import record_consent_event
from app.models.consent import ConsentVersion, PlatformConsent, RelationshipConsent
from app.models.user import User


SUPPORTED_RELATIONSHIP_CONSENT_TYPES = ("provider_access", "caregiver_access")
SUPPORTED_RELATIONSHIP_STATES = ("PENDING", "ACTIVE", "REJECTED", "REVOKED", "EXPIRED")
INACTIVE_RELATIONSHIP_STATES = ("REJECTED", "REVOKED", "EXPIRED")
REQUESTOR_ROLE_BY_CONSENT_TYPE = {
    "provider_access": "provider",
    "caregiver_access": "caregiver",
}


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


def _now():
    return datetime.now(timezone.utc)


def _clean_alias(alias: str, default_alias: str):
    cleaned = (alias or default_alias or "").strip()
    if not cleaned:
        raise ValueError("Alias is required")
    if len(cleaned) > 60:
        raise ValueError("Alias must be 60 characters or fewer")
    return cleaned


def _get_relationship_consent(db: Session, consent_id: int):
    consent = db.query(RelationshipConsent).filter(RelationshipConsent.id == consent_id).first()
    if consent is None:
        raise ValueError("Consent request not found")
    return consent


def _ensure_patient_authority(consent: RelationshipConsent, actor_user: User):
    if actor_user.role != "patient" or consent.patient_id != actor_user.id:
        raise PermissionError("Patient authority is required for this consent")


def _ensure_requestor_matches_consent_type(actor_user: User, consent_type: str):
    expected_role = REQUESTOR_ROLE_BY_CONSENT_TYPE.get(consent_type)
    if actor_user.role != expected_role:
        raise ValueError(f"{expected_role} role is required for {consent_type}")


def create_consent_request(
    db: Session,
    *,
    patient_id: int,
    requestor_user: User,
    consent_type: str,
    alias: str = None,
    session_id: int = None,
    ip_address: str = None,
):
    validate_consent_request(consent_type)
    _ensure_requestor_matches_consent_type(requestor_user, consent_type)

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if patient is None:
        raise ValueError("A registered patient is required")
    if patient.id == requestor_user.id:
        raise ValueError("Patients cannot request relationship consent from themselves")

    existing = (
        db.query(RelationshipConsent)
        .filter(
            RelationshipConsent.patient_id == patient.id,
            RelationshipConsent.requestor_id == requestor_user.id,
            RelationshipConsent.consent_type == consent_type,
            RelationshipConsent.status.in_(("PENDING", "ACTIVE")),
        )
        .first()
    )
    if existing is not None:
        raise ValueError("An active or pending consent already exists")

    consent = RelationshipConsent(
        patient_id=patient.id,
        requestor_id=requestor_user.id,
        requestor_role=requestor_user.role,
        consent_type=consent_type,
        alias=_clean_alias(alias, requestor_user.full_name),
        status="PENDING",
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    record_consent_event(
        db,
        "consent.request",
        consent,
        actor_user=requestor_user,
        session_id=session_id,
        previous_state=None,
        new_state=consent.status,
        ip_address=ip_address,
    )
    return consent


def get_relationship_consent(db: Session, *, consent_id: int):
    return _get_relationship_consent(db, consent_id)


def get_active_consents(db: Session, *, patient_id: int):
    return (
        db.query(RelationshipConsent)
        .filter(RelationshipConsent.patient_id == patient_id, RelationshipConsent.status == "ACTIVE")
        .order_by(RelationshipConsent.granted_at.desc(), RelationshipConsent.requested_at.desc())
        .all()
    )


def get_pending_consents(db: Session, *, patient_id: int):
    return (
        db.query(RelationshipConsent)
        .filter(RelationshipConsent.patient_id == patient_id, RelationshipConsent.status == "PENDING")
        .order_by(RelationshipConsent.requested_at.desc())
        .all()
    )


def get_inactive_consents(db: Session, *, patient_id: int):
    return (
        db.query(RelationshipConsent)
        .filter(
            RelationshipConsent.patient_id == patient_id,
            RelationshipConsent.status.in_(INACTIVE_RELATIONSHIP_STATES),
        )
        .order_by(
            RelationshipConsent.revoked_at.desc(),
            RelationshipConsent.rejected_at.desc(),
            RelationshipConsent.expired_at.desc(),
            RelationshipConsent.requested_at.desc(),
        )
        .all()
    )


def get_pending_consent_requests(db: Session, *, patient_id: int):
    return get_pending_consents(db, patient_id=patient_id)


def grant_consent(
    db: Session,
    *,
    consent_id: int,
    actor_user: User,
    session_id: int,
    ip_address: str = None,
):
    consent = _get_relationship_consent(db, consent_id)
    _ensure_patient_authority(consent, actor_user)
    if consent.status != "PENDING":
        raise ValueError("Only pending consent can be granted")

    previous_state = consent.status
    consent.status = "ACTIVE"
    consent.granted_at = _now()
    db.commit()
    db.refresh(consent)
    record_consent_event(
        db,
        "consent.grant",
        consent,
        actor_user=actor_user,
        session_id=session_id,
        previous_state=previous_state,
        new_state=consent.status,
        ip_address=ip_address,
    )
    from app.relationships.relationship_service import (
        create_patient_caregiver_link,
        create_provider_patient_link,
    )

    if consent.requestor_role == "provider":
        create_provider_patient_link(
            db,
            provider=consent.requestor,
            patient_id=consent.patient_id,
            actor_user=actor_user,
            ip_address=ip_address,
        )
    else:
        create_patient_caregiver_link(
            db,
            caregiver=consent.requestor,
            patient_id=consent.patient_id,
            actor_user=actor_user,
            ip_address=ip_address,
        )
    return consent


def reject_consent(
    db: Session,
    *,
    consent_id: int,
    actor_user: User,
    session_id: int,
    ip_address: str = None,
):
    consent = _get_relationship_consent(db, consent_id)
    _ensure_patient_authority(consent, actor_user)
    if consent.status != "PENDING":
        raise ValueError("Only pending consent can be rejected")

    previous_state = consent.status
    consent.status = "REJECTED"
    consent.rejected_at = _now()
    db.commit()
    db.refresh(consent)
    record_consent_event(
        db,
        "consent.reject",
        consent,
        actor_user=actor_user,
        session_id=session_id,
        previous_state=previous_state,
        new_state=consent.status,
        ip_address=ip_address,
    )
    return consent


def revoke_consent(
    db: Session,
    *,
    consent_id: int,
    actor_user: User,
    session_id: int,
    ip_address: str = None,
):
    consent = _get_relationship_consent(db, consent_id)
    _ensure_patient_authority(consent, actor_user)
    if consent.status != "ACTIVE":
        raise ValueError("Only active consent can be revoked")

    previous_state = consent.status
    consent.status = "REVOKED"
    consent.revoked_at = _now()
    db.commit()
    db.refresh(consent)
    record_consent_event(
        db,
        "consent.revoke",
        consent,
        actor_user=actor_user,
        session_id=session_id,
        previous_state=previous_state,
        new_state=consent.status,
        ip_address=ip_address,
    )
    from app.relationships.relationship_service import deactivate_links_for_consent

    deactivate_links_for_consent(
        db,
        consent_id=consent.id,
        actor_user=actor_user,
        ip_address=ip_address,
    )
    return consent


def update_consent_alias(
    db: Session,
    *,
    consent_id: int,
    actor_user: User,
    alias: str,
):
    consent = _get_relationship_consent(db, consent_id)
    _ensure_patient_authority(consent, actor_user)
    consent.alias = _clean_alias(alias, consent.requestor.full_name)
    db.commit()
    db.refresh(consent)
    return consent
