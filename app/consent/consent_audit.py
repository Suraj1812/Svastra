import json

from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.models.consent import ConsentCEPEvent, RelationshipConsent


def consent_event_payload(consent: RelationshipConsent, extra: dict = None):
    payload = {
        "consent_id": consent.id,
        "patient_id": consent.patient_id,
        "requestor_id": consent.requestor_id,
        "requestor_role": consent.requestor_role,
        "consent_type": consent.consent_type,
        "status": consent.status,
    }
    payload.update(extra or {})
    return payload


def record_consent_event(
    db: Session,
    event_name: str,
    consent: RelationshipConsent,
    actor_user=None,
    ip_address: str = None,
    success: bool = True,
    metadata: dict = None,
):
    payload = consent_event_payload(consent, metadata)
    record_audit_event(
        db,
        action=event_name,
        actor_user_id=actor_user.id if actor_user is not None else None,
        actor_role=actor_user.role if actor_user is not None else None,
        mobile_number=actor_user.mobile_number if actor_user is not None else None,
        ip_address=ip_address,
        success=success,
        metadata=payload,
    )

    cep_event = ConsentCEPEvent(
        event_name=event_name,
        consent_id=consent.id,
        payload_json=json.dumps(payload, sort_keys=True, default=str),
    )
    db.add(cep_event)
    db.commit()
    db.refresh(cep_event)
    return cep_event
