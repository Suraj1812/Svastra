from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.models.relationship import PatientCaregiverLink, ProviderPatientLink
from app.models.user import User
from app.postoffice.dispatcher import create_event, dispatch_event, send_event
from app.reference_terms import decode_reference_term
from app.relationships.relationship_validator import (
    RelationshipValidationError,
    relationship_for_party,
    validate_linkage,
)


def _now():
    return datetime.now(timezone.utc)


def _relationship_payload(link):
    if isinstance(link, ProviderPatientLink):
        return {
            "relationship_id": link.link_id,
            "patient_id": link.patient_id,
            "linked_user_id": link.provider_id,
            "actor_id": link.provider_id,
            "relationship_type": "provider_patient",
            "consent_request_id": link.source_consent_id,
            "status": "ACTIVE" if link.status == "active" else "INACTIVE",
        }
    return {
        "relationship_id": link.link_id,
        "patient_id": link.patient_id,
        "linked_user_id": link.caregiver_id,
        "actor_id": link.caregiver_id,
        "relationship_type": "patient_caregiver",
        "consent_request_id": link.source_consent_id,
        "status": "ACTIVE" if link.status == "active" else "INACTIVE",
    }


def _record_relationship_event(db: Session, *, action: str, link, actor_user: User, ip_address=None):
    payload = _relationship_payload(link)
    payload["timestamp"] = _now().isoformat()
    record_audit_event(
        db,
        action=action,
        actor_user_id=actor_user.id,
        actor_role=actor_user.role,
        mobile_number=actor_user.mobile_number,
        ip_address=ip_address,
        metadata=payload,
    )
    event = create_event(event_type=action, source="svastra_backend", payload=payload)
    outbound, _, _ = send_event(db, event)
    dispatch_event(db, outbound.event_id)


def create_provider_patient_link(
    db: Session, *, provider: User, patient_id: int, actor_user: User | None = None, ip_address=None
):
    if provider.role != "provider":
        raise RelationshipValidationError("Provider role is required")
    patient, consent = validate_linkage(db, linked_user=provider, patient_id=patient_id)
    link = db.query(ProviderPatientLink).filter(
        ProviderPatientLink.provider_id == provider.id,
        ProviderPatientLink.patient_id == patient.id,
    ).order_by(ProviderPatientLink.created_at.desc()).first()
    if link is not None and link.status == "active":
        return link, False
    if link is None:
        link = ProviderPatientLink(
            link_id=f"link_pp_{uuid4().hex}",
            provider_id=provider.id,
            patient_id=patient.id,
            source_consent_id=consent.id,
            status="active",
        )
        db.add(link)
    else:
        link.source_consent_id = consent.id
        link.status = "active"
        link.ended_at = None
    db.commit()
    db.refresh(link)
    _record_relationship_event(
        db, action="relationship.created", link=link, actor_user=actor_user or provider, ip_address=ip_address
    )
    return link, True


def create_patient_caregiver_link(
    db: Session, *, caregiver: User, patient_id: int, actor_user: User | None = None, ip_address=None
):
    if caregiver.role != "caregiver":
        raise RelationshipValidationError("Caregiver role is required")
    patient, consent = validate_linkage(db, linked_user=caregiver, patient_id=patient_id)
    link = db.query(PatientCaregiverLink).filter(
        PatientCaregiverLink.caregiver_id == caregiver.id,
        PatientCaregiverLink.patient_id == patient.id,
    ).order_by(PatientCaregiverLink.created_at.desc()).first()
    if link is not None and link.status == "active":
        return link, False
    relationship_term = decode_reference_term(caregiver.relationship_to_patient, "relationship") or {}
    if link is None:
        link = PatientCaregiverLink(
            link_id=f"link_pc_{uuid4().hex}",
            caregiver_id=caregiver.id,
            patient_id=patient.id,
            source_consent_id=consent.id,
            relationship_type=relationship_term.get("term", "Caregiver"),
            status="active",
        )
        db.add(link)
    else:
        link.source_consent_id = consent.id
        link.status = "active"
        link.ended_at = None
    db.commit()
    db.refresh(link)
    _record_relationship_event(
        db, action="relationship.created", link=link, actor_user=actor_user or caregiver, ip_address=ip_address
    )
    return link, True


def get_provider_patients(db: Session, *, provider_id: int, include_inactive: bool = True):
    query = db.query(ProviderPatientLink).filter(ProviderPatientLink.provider_id == provider_id)
    if not include_inactive:
        query = query.filter(ProviderPatientLink.status == "active")
    return query.order_by(ProviderPatientLink.created_at.desc()).all()


def get_patient_providers(db: Session, *, patient_id: int, include_inactive: bool = True):
    query = db.query(ProviderPatientLink).filter(ProviderPatientLink.patient_id == patient_id)
    if not include_inactive:
        query = query.filter(ProviderPatientLink.status == "active")
    return query.order_by(ProviderPatientLink.created_at.desc()).all()


def get_patient_caregivers(db: Session, *, patient_id: int, include_inactive: bool = True):
    query = db.query(PatientCaregiverLink).filter(PatientCaregiverLink.patient_id == patient_id)
    if not include_inactive:
        query = query.filter(PatientCaregiverLink.status == "active")
    return query.order_by(PatientCaregiverLink.created_at.desc()).all()


def get_caregiver_patients(db: Session, *, caregiver_id: int, include_inactive: bool = True):
    query = db.query(PatientCaregiverLink).filter(PatientCaregiverLink.caregiver_id == caregiver_id)
    if not include_inactive:
        query = query.filter(PatientCaregiverLink.status == "active")
    return query.order_by(PatientCaregiverLink.created_at.desc()).all()


def deactivate_relationship(db: Session, *, link_id: str, actor_user: User, ip_address=None):
    link = relationship_for_party(db, link_id=link_id, current_user=actor_user)
    if link.status == "ended":
        return link, False
    link.status = "ended"
    link.ended_at = _now()
    db.commit()
    db.refresh(link)
    _record_relationship_event(
        db,
        action="relationship.deactivated",
        link=link,
        actor_user=actor_user,
        ip_address=ip_address,
    )
    return link, True


def deactivate_links_for_consent(db: Session, *, consent_id: int, actor_user: User, ip_address=None):
    links = []
    provider_link = db.query(ProviderPatientLink).filter(
        ProviderPatientLink.source_consent_id == consent_id,
        ProviderPatientLink.status == "active",
    ).first()
    caregiver_link = db.query(PatientCaregiverLink).filter(
        PatientCaregiverLink.source_consent_id == consent_id,
        PatientCaregiverLink.status == "active",
    ).first()
    for link in (provider_link, caregiver_link):
        if link is not None:
            link.status = "ended"
            link.ended_at = _now()
            db.commit()
            db.refresh(link)
            _record_relationship_event(
                db,
                action="relationship.deactivated",
                link=link,
                actor_user=actor_user,
                ip_address=ip_address,
            )
            links.append(link)
    return links


def serialize_relationship(link, *, viewer_id: int | None = None, include_mobile: bool = False):
    if isinstance(link, ProviderPatientLink):
        linked_user = link.provider
        patient = link.patient
        relationship_type = "provider_patient"
        role = "provider"
    else:
        linked_user = link.caregiver
        patient = link.patient
        relationship_type = "patient_caregiver"
        role = "caregiver"
    data = {
        "id": link.link_id,
        "patient": {"id": patient.id, "full_name": patient.full_name},
        "linked_user": {
            "id": linked_user.id,
            "full_name": linked_user.full_name,
            "role": role,
        },
        "alias": patient.full_name if viewer_id == linked_user.id else link.source_consent.alias,
        "relationship_type": relationship_type,
        "relationship_status": "ACTIVE" if link.status == "active" else "INACTIVE",
        "consent_request_id": link.source_consent_id,
        "relationship_date": link.created_at,
        "deactivated_at": link.ended_at,
    }
    if include_mobile:
        data["mobile_number"] = patient.mobile_number if viewer_id == linked_user.id else linked_user.mobile_number
    return data
