from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.consent import RelationshipConsent
from app.models.relationship import PatientCaregiverLink, ProviderPatientLink
from app.models.user import User


class RelationshipValidationError(ValueError):
    pass


def active_linkage_consent(db: Session, *, linked_user: User, patient_id: int):
    consent_type = {
        "provider": "provider_access",
        "caregiver": "caregiver_access",
    }.get(linked_user.role)
    if consent_type is None:
        return None
    return db.query(RelationshipConsent).filter(
        RelationshipConsent.patient_id == patient_id,
        RelationshipConsent.requestor_id == linked_user.id,
        RelationshipConsent.consent_type == consent_type,
        RelationshipConsent.status == "ACTIVE",
    ).first()


def validate_relationship_parties(db: Session, *, linked_user: User, patient_id: int):
    if linked_user.role not in ("provider", "caregiver"):
        raise RelationshipValidationError("Only providers and caregivers can link to patients")
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if patient is None or not patient.is_active:
        raise RelationshipValidationError("An active registered patient is required")
    if not linked_user.is_active:
        raise RelationshipValidationError("The provider or caregiver account is inactive")
    return patient


def validate_linkage(db: Session, *, linked_user: User, patient_id: int):
    patient = validate_relationship_parties(db, linked_user=linked_user, patient_id=patient_id)
    consent = active_linkage_consent(db, linked_user=linked_user, patient_id=patient_id)
    if consent is None:
        raise RelationshipValidationError("Active patient consent is required before linkage")
    return patient, consent


def has_active_provider_relationship(db: Session, *, provider_id: int, patient_id: int):
    link = db.query(ProviderPatientLink).filter(
        ProviderPatientLink.provider_id == provider_id,
        ProviderPatientLink.patient_id == patient_id,
        ProviderPatientLink.status == "active",
    ).first()
    return link is not None and link.source_consent.status == "ACTIVE"


def has_active_caregiver_relationship(db: Session, *, caregiver_id: int, patient_id: int):
    link = db.query(PatientCaregiverLink).filter(
        PatientCaregiverLink.caregiver_id == caregiver_id,
        PatientCaregiverLink.patient_id == patient_id,
        PatientCaregiverLink.status == "active",
    ).first()
    return link is not None and link.source_consent.status == "ACTIVE"


def validate_relationship_access(db: Session, *, linked_user_id: int, patient_id: int, role: str):
    if role == "provider" and has_active_provider_relationship(
        db, provider_id=linked_user_id, patient_id=patient_id
    ):
        return True
    if role == "caregiver" and has_active_caregiver_relationship(
        db, caregiver_id=linked_user_id, patient_id=patient_id
    ):
        return True
    raise RelationshipValidationError("An active consent-backed healthcare relationship is required")


def validate_patient_scope(db: Session, *, current_user: User, patient_id: int):
    if current_user.role == "patient":
        if current_user.id != patient_id:
            raise RelationshipValidationError("Patients may access only their own data")
        return True
    return validate_relationship_access(
        db,
        linked_user_id=current_user.id,
        patient_id=patient_id,
        role=current_user.role,
    )


def relationship_for_party(db: Session, *, link_id: str, current_user: User):
    provider_link = db.query(ProviderPatientLink).filter(
        ProviderPatientLink.link_id == link_id,
        or_(
            ProviderPatientLink.provider_id == current_user.id,
            ProviderPatientLink.patient_id == current_user.id,
        ),
    ).first()
    if provider_link is not None:
        return provider_link
    caregiver_link = db.query(PatientCaregiverLink).filter(
        PatientCaregiverLink.link_id == link_id,
        or_(
            PatientCaregiverLink.caregiver_id == current_user.id,
            PatientCaregiverLink.patient_id == current_user.id,
        ),
    ).first()
    if caregiver_link is not None:
        return caregiver_link
    raise RelationshipValidationError("Relationship not found")
