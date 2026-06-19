from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.models.care import CarePlan
from app.models.consent import RelationshipConsent
from app.models.postoffice import (
    OutboundEvent,
    PostOfficeAcknowledgement,
    ReceivedEvent,
    TimelineEvent,
)
from app.models.relationship import PatientCaregiverLink, ProviderPatientLink
from app.models.user import User
from app.postoffice.router import route_event
from app.postoffice.validators import CEPEvent, CEPValidationError, validate_event


def _utcnow():
    return datetime.now(timezone.utc)


def create_event(*, event_type: str, source: str, payload: dict):
    return CEPEvent(
        event_type=event_type,
        event_id=f"evt_{uuid4().hex}",
        timestamp=_utcnow(),
        source=source,
        payload=payload,
    )


def _authorize_event(db: Session, event: CEPEvent, actor_user: User | None):
    patient = db.query(User).filter(User.id == event.payload["patient_id"], User.role == "patient").first()
    if patient is None or not patient.is_active:
        raise CEPValidationError("payload.patient_id must identify an active patient")
    if actor_user is None:
        return patient
    if event.payload["actor_id"] != actor_user.id:
        raise PermissionError("CEP actor_id must match the authenticated user")

    if event.event_type.startswith("consent."):
        consent = db.query(RelationshipConsent).filter(
            RelationshipConsent.id == event.payload["consent_id"]
        ).first()
        if consent is None or consent.patient_id != patient.id:
            raise PermissionError("CEP consent does not belong to this patient")
        if event.event_type == "consent.request" and consent.requestor_id != actor_user.id:
            raise PermissionError("Only the consent requestor may send this event")
        if event.event_type != "consent.request" and patient.id != actor_user.id:
            raise PermissionError("Only the patient may send a consent decision event")
        if consent.status != event.payload["status"]:
            raise CEPValidationError("CEP consent status does not match stored state")
    elif event.event_type.startswith("relationship."):
        relationship = db.query(ProviderPatientLink).filter(
            ProviderPatientLink.link_id == event.payload["relationship_id"]
        ).first()
        if relationship is None:
            relationship = db.query(PatientCaregiverLink).filter(
                PatientCaregiverLink.link_id == event.payload["relationship_id"]
            ).first()
        if relationship is None or relationship.patient_id != patient.id:
            raise PermissionError("CEP relationship does not belong to this patient")
        linked_user_id = (
            relationship.provider_id
            if isinstance(relationship, ProviderPatientLink)
            else relationship.caregiver_id
        )
        if actor_user.id not in (relationship.patient_id, linked_user_id):
            raise PermissionError("User is not a party to this relationship")
        serialized_status = "ACTIVE" if relationship.status == "active" else "INACTIVE"
        if serialized_status != event.payload["status"]:
            raise CEPValidationError("CEP relationship status does not match stored state")
    elif event.event_type == "advisory.publish":
        plan = db.query(CarePlan).filter(CarePlan.id == event.payload["care_plan_id"]).first()
        if plan is None or plan.patient_id != patient.id or plan.provider_id != actor_user.id:
            raise PermissionError("Only the owning provider may publish this care plan event")
    elif actor_user.role == "patient":
        if actor_user.id != patient.id:
            raise PermissionError("Patients may send events only for themselves")
    else:
        if actor_user.role == "provider":
            relationship = db.query(ProviderPatientLink).filter(
                ProviderPatientLink.patient_id == patient.id,
                ProviderPatientLink.provider_id == actor_user.id,
                ProviderPatientLink.status == "active",
            ).first()
        elif actor_user.role == "caregiver":
            relationship = db.query(PatientCaregiverLink).filter(
                PatientCaregiverLink.patient_id == patient.id,
                PatientCaregiverLink.caregiver_id == actor_user.id,
                PatientCaregiverLink.status == "active",
            ).first()
        else:
            relationship = None
        if relationship is None or relationship.source_consent.status != "ACTIVE":
            raise PermissionError("An active consent-backed relationship is required")
    return patient


def _serialize_event(event: CEPEvent):
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def send_event(
    db: Session,
    event: CEPEvent | dict,
    *,
    actor_user: User | None = None,
    commit: bool = True,
):
    event = validate_event(event)
    patient = _authorize_event(db, event, actor_user)
    route = route_event(event)

    existing = db.query(OutboundEvent).filter(OutboundEvent.event_id == event.event_id).first()
    if existing is not None:
        return existing, route, True
    existing_timeline = db.query(TimelineEvent).filter(TimelineEvent.event_id == event.event_id).first()
    if existing_timeline is not None:
        raise CEPValidationError("event_id already exists in the immutable timeline")

    serialized = _serialize_event(event)
    timeline = TimelineEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        patient_id=patient.id,
        actor_id=str(event.payload["actor_id"]),
        source_app=event.source,
        target_app=route.target_app,
        payload_json=serialized,
        occurred_at=event.timestamp,
    )
    outbound = OutboundEvent(
        event_id=event.event_id,
        patient_id=patient.id,
        target_app=route.target_app,
        cep_json=serialized,
        status="pending",
        retry_count=0,
    )
    db.add_all([timeline, outbound])
    if commit:
        db.commit()
        db.refresh(outbound)
    else:
        db.flush()
    return outbound, route, False


def dispatch_event(db: Session, event_id: str):
    outbound = db.query(OutboundEvent).filter(OutboundEvent.event_id == event_id).first()
    if outbound is None:
        raise ValueError("Outbound event not found")
    if outbound.status == "sent":
        return outbound

    outbound.retry_count += 1
    outbound.last_attempt_at = _utcnow()
    outbound.status = "sent"
    db.commit()
    db.refresh(outbound)
    return outbound


def acknowledge_event(
    db: Session,
    *,
    event_id: str,
    received_by: str,
    status: str = "received",
    actor_user: User | None = None,
):
    outbound = db.query(OutboundEvent).filter(OutboundEvent.event_id == event_id).first()
    if outbound is None:
        existing = db.query(PostOfficeAcknowledgement).filter(
            PostOfficeAcknowledgement.event_id == event_id
        ).first()
        if existing is not None:
            return existing, True
        raise ValueError("Outbound event not found")
    if outbound.status != "sent":
        raise ValueError("Event must be dispatched before acknowledgement")
    if received_by != outbound.target_app:
        raise PermissionError("Acknowledgement receiver does not match the routed target")
    if status != "received":
        raise ValueError("Only received acknowledgements are supported")

    acknowledged_at = _utcnow()
    acknowledgement = PostOfficeAcknowledgement(
        ack_id=f"ack_{uuid4().hex}",
        event_id=event_id,
        received_by=received_by,
        status=status,
        received_at=acknowledged_at,
    )
    received_event = ReceivedEvent(
        event_id=event_id,
        target_app=received_by,
        cep_json=outbound.cep_json,
    )
    db.add_all([acknowledgement, received_event])
    db.delete(outbound)
    db.commit()
    db.refresh(acknowledgement)
    record_audit_event(
        db,
        action="postoffice.acknowledged",
        actor_user_id=actor_user.id if actor_user else None,
        actor_role=actor_user.role if actor_user else "system",
        success=True,
        metadata={
            "event_id": event_id,
            "ack_id": acknowledgement.ack_id,
            "received_by": received_by,
            "status": status,
        },
    )
    return acknowledgement, False


def serialize_outbound(outbound: OutboundEvent):
    return {
        "event_id": outbound.event_id,
        "patient_id": outbound.patient_id,
        "target_app": outbound.target_app,
        "status": outbound.status,
        "retry_count": outbound.retry_count,
        "created_at": outbound.created_at,
        "last_attempt_at": outbound.last_attempt_at,
    }


def serialize_acknowledgement(acknowledgement: PostOfficeAcknowledgement):
    return {
        "ack_id": acknowledgement.ack_id,
        "event_id": acknowledgement.event_id,
        "received_by": acknowledgement.received_by,
        "status": acknowledgement.status,
        "received_at": acknowledgement.received_at,
    }
