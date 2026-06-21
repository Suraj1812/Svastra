from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.config import settings
from app.models.care import Advisory, CarePlan
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
    expected_source = {
        "provider": "mantrana_mitra",
        "patient": "rogi_mitra",
        "caregiver": "sahay_mitra",
    }.get(actor_user.role)
    if expected_source is None or event.source != expected_source:
        raise PermissionError("CEP source does not match the authenticated application role")

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
        relationship = db.query(ProviderPatientLink).filter(
            ProviderPatientLink.patient_id == patient.id,
            ProviderPatientLink.provider_id == actor_user.id,
            ProviderPatientLink.status == "active",
        ).first()
        if relationship is None or relationship.source_consent.status != "ACTIVE":
            raise PermissionError("An active consent-backed provider relationship is required")
        if event.payload.get("title") != plan.title or event.payload.get("diagnosis") != plan.diagnosis:
            raise CEPValidationError("CEP care-plan context does not match stored state")
        advisory_ids: set[int] = set()
        for item in event.payload["advisories"]:
            if item["advisory_id"] in advisory_ids:
                raise CEPValidationError("CEP advisories cannot contain duplicate advisory_id values")
            advisory_ids.add(item["advisory_id"])
            stored = db.query(Advisory).filter(
                Advisory.id == item["advisory_id"],
                Advisory.care_plan_id == plan.id,
                Advisory.provider_id == actor_user.id,
                Advisory.patient_id == patient.id,
            ).first()
            if stored is None:
                raise CEPValidationError("CEP advisory does not belong to the published care plan")
            if (
                stored.status != "PUBLISHED"
                or stored.execution_status != "pending"
                or stored.concept_id != item["concept_id"]
                or stored.term != item["term"]
                or stored.advisory_type != item["advisory_type"]
                or stored.tag != item["tag"]
                or json.loads(stored.configuration_json) != item["configuration"]
            ):
                raise CEPValidationError("CEP advisory does not match the immutable stored state")
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


def _related_user_id(event: CEPEvent):
    related = event.payload.get("requestor_id") or event.payload.get("linked_user_id")
    if related is None and event.payload["actor_id"] != event.payload["patient_id"]:
        related = event.payload["actor_id"]
    return related


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
    serialized = _serialize_event(event)

    existing = db.query(OutboundEvent).filter(OutboundEvent.event_id == event.event_id).first()
    if existing is not None:
        if existing.cep_json != serialized:
            raise CEPValidationError("event_id is already queued with a different immutable payload")
        return existing, route, True
    existing_timeline = db.query(TimelineEvent).filter(TimelineEvent.event_id == event.event_id).first()
    if existing_timeline is not None:
        raise CEPValidationError("event_id already exists in the immutable timeline")

    timeline = TimelineEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        patient_id=patient.id,
        actor_id=str(event.payload["actor_id"]),
        related_user_id=_related_user_id(event),
        source_app=event.source,
        target_app=route.target_app,
        payload_json=serialized,
        payload_sha256=sha256(serialized.encode("utf-8")).hexdigest(),
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
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            concurrent = db.query(OutboundEvent).filter(
                OutboundEvent.event_id == event.event_id
            ).first()
            if concurrent is not None and concurrent.cep_json == serialized:
                return concurrent, route, True
            raise CEPValidationError("event_id conflicts with an existing immutable event") from error
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
    if outbound.retry_count >= settings.postoffice_max_retries:
        raise ValueError(
            f"PostOffice retry limit of {settings.postoffice_max_retries} has been reached"
        )

    outbound.retry_count += 1
    outbound.last_attempt_at = _utcnow()
    outbound.status = "sent"
    outbound.last_error_code = None
    outbound.last_error_message = None
    db.commit()
    db.refresh(outbound)
    return outbound


def mark_event_failed(db: Session, *, event_id: str, error_code: str, error_message: str):
    outbound = db.query(OutboundEvent).filter(OutboundEvent.event_id == event_id).first()
    if outbound is None:
        raise ValueError("Outbound event not found")
    outbound.status = "failed"
    outbound.last_error_code = error_code[:64]
    outbound.last_error_message = error_message[:255]
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
            if existing.received_by != received_by or existing.status != status:
                raise PermissionError("Acknowledgement conflicts with the immutable receipt")
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
        retry_count=outbound.retry_count,
        last_attempt_at=outbound.last_attempt_at,
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
        "last_error": (
            {"code": outbound.last_error_code, "message": outbound.last_error_message}
            if outbound.last_error_code or outbound.last_error_message
            else None
        ),
    }


def serialize_acknowledgement(acknowledgement: PostOfficeAcknowledgement):
    return {
        "ack_id": acknowledgement.ack_id,
        "event_id": acknowledgement.event_id,
        "received_by": acknowledgement.received_by,
        "status": acknowledgement.status,
        "retry_count": acknowledgement.retry_count,
        "last_attempt_at": acknowledgement.last_attempt_at,
        "received_at": acknowledgement.received_at,
    }
