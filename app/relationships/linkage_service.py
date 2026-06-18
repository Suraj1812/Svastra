from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.models.consent import RelationshipConsent
from app.models.relationship import HealthcareRelationship
from app.models.user import User
from app.relationships.relationship_validator import validate_linkage


def serialize_linkage(relationship: HealthcareRelationship):
    return {
        "id": relationship.id,
        "patient": {
            "id": relationship.patient.id,
            "full_name": relationship.patient.full_name,
            "mobile_number": relationship.patient.mobile_number,
        },
        "linked_user": {
            "id": relationship.linked_user.id,
            "full_name": relationship.linked_user.full_name,
            "role": relationship.linked_user.role,
        },
        "relationship_type": relationship.relationship_type,
        "source_consent_id": relationship.source_consent_id,
        "status": relationship.status,
        "linked_at": relationship.linked_at,
    }


def link_patient(db: Session, *, linked_user: User, patient_id: int, ip_address: str = None):
    patient, consent, relationship_type = validate_linkage(
        db,
        linked_user=linked_user,
        patient_id=patient_id,
    )
    relationship = HealthcareRelationship(
        patient_id=patient.id,
        linked_user_id=linked_user.id,
        relationship_type=relationship_type,
        source_consent_id=consent.id,
        status="ACTIVE",
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)
    record_audit_event(
        db,
        action="relationship.link",
        actor_user_id=linked_user.id,
        actor_role=linked_user.role,
        mobile_number=linked_user.mobile_number,
        ip_address=ip_address,
        metadata={
            "relationship_id": relationship.id,
            "patient_id": patient.id,
            "relationship_type": relationship_type,
            "source_consent_id": consent.id,
        },
    )
    return relationship


def get_linked_patients(db: Session, *, linked_user_id: int):
    return (
        db.query(HealthcareRelationship)
        .filter(
            HealthcareRelationship.linked_user_id == linked_user_id,
            HealthcareRelationship.status == "ACTIVE",
        )
        .order_by(HealthcareRelationship.linked_at.desc())
        .all()
    )


def get_patient_relationships(db: Session, *, patient_id: int):
    return (
        db.query(HealthcareRelationship)
        .filter(
            HealthcareRelationship.patient_id == patient_id,
            HealthcareRelationship.status == "ACTIVE",
        )
        .order_by(HealthcareRelationship.linked_at.desc())
        .all()
    )


def get_linkable_patients(db: Session, *, linked_user: User):
    active_consents = (
        db.query(RelationshipConsent)
        .filter(
            RelationshipConsent.requestor_id == linked_user.id,
            RelationshipConsent.status == "ACTIVE",
        )
        .order_by(RelationshipConsent.granted_at.desc())
        .all()
    )
    linked_patient_ids = {
        relationship.patient_id
        for relationship in get_linked_patients(db, linked_user_id=linked_user.id)
    }
    return [
        {
            "patient": {
                "id": consent.patient.id,
                "full_name": consent.patient.full_name,
                "mobile_number": consent.patient.mobile_number,
            },
            "consent_id": consent.id,
            "consent_type": consent.consent_type,
            "granted_at": consent.granted_at,
        }
        for consent in active_consents
        if consent.patient_id not in linked_patient_ids
    ]
