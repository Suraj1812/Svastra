from sqlalchemy.orm import Session

from app.models.consent import RelationshipConsent


ACTIVE_STATE = "ACTIVE"


class ConsentAccessDenied(PermissionError):
    pass


def _active_consent(
    db: Session,
    *,
    patient_id: int,
    requestor_id: int,
    consent_type: str,
):
    return (
        db.query(RelationshipConsent)
        .filter(
            RelationshipConsent.patient_id == patient_id,
            RelationshipConsent.requestor_id == requestor_id,
            RelationshipConsent.consent_type == consent_type,
            RelationshipConsent.status == ACTIVE_STATE,
        )
        .first()
    )


def has_provider_access(db: Session, *, provider_id: int, patient_id: int):
    return (
        _active_consent(
            db,
            patient_id=patient_id,
            requestor_id=provider_id,
            consent_type="provider_access",
        )
        is not None
    )


def has_caregiver_access(db: Session, *, caregiver_id: int, patient_id: int):
    return (
        _active_consent(
            db,
            patient_id=patient_id,
            requestor_id=caregiver_id,
            consent_type="caregiver_access",
        )
        is not None
    )


def validate_access(
    db: Session,
    *,
    patient_id: int,
    requestor_id: int,
    consent_type: str,
):
    consent = _active_consent(
        db,
        patient_id=patient_id,
        requestor_id=requestor_id,
        consent_type=consent_type,
    )
    if consent is None:
        raise ConsentAccessDenied("Active relationship consent is required")
    return consent
