from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.audit.audit_service import record_audit_event
from app.care.advisory_service import serialize_advisory
from app.models.care import Advisory, CarePlan
from app.models.user import User
from app.postoffice.dispatcher import create_event, dispatch_event, send_event
from app.relationships.relationship_validator import has_active_provider_relationship


def _get_care_plan(db: Session, care_plan_id: int):
    plan = db.query(CarePlan).options(joinedload(CarePlan.advisories)).filter(
        CarePlan.id == care_plan_id
    ).first()
    if plan is None:
        raise ValueError("Care plan not found")
    return plan


def create_care_plan(
    db: Session,
    *,
    provider: User,
    patient_id: int,
    title: str,
    diagnosis: str | None = None,
    ip_address: str | None = None,
):
    if provider.role != "provider":
        raise PermissionError("Provider role is required")
    if not has_active_provider_relationship(
        db,
        provider_id=provider.id,
        patient_id=patient_id,
    ):
        raise PermissionError("Only a consent-backed linked provider can create a care plan")
    plan = CarePlan(
        provider_id=provider.id,
        patient_id=patient_id,
        title=title,
        diagnosis=diagnosis,
        status="DRAFT",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    record_audit_event(
        db,
        action="care_plan.created",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={"care_plan_id": plan.id, "patient_id": patient_id},
    )
    return plan


def get_provider_care_plans(db: Session, *, provider_id: int, patient_id: int | None = None):
    query = db.query(CarePlan).options(joinedload(CarePlan.advisories)).filter(
        CarePlan.provider_id == provider_id
    )
    if patient_id is not None:
        query = query.filter(CarePlan.patient_id == patient_id)
    return query.order_by(CarePlan.updated_at.desc()).all()


def get_provider_care_plan(db: Session, *, care_plan_id: int, provider: User):
    plan = _get_care_plan(db, care_plan_id)
    if plan.provider_id != provider.id:
        raise PermissionError("Care plan is not owned by this provider")
    return plan


def publish_care_plan(
    db: Session,
    *,
    care_plan_id: int,
    provider: User,
    ip_address: str | None = None,
):
    plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=provider)
    if plan.status != "DRAFT":
        raise ValueError("Care plan is already published and immutable")
    if not plan.advisories:
        raise ValueError("Add at least one valid advisory before publishing")
    if not has_active_provider_relationship(
        db,
        provider_id=provider.id,
        patient_id=plan.patient_id,
    ):
        raise PermissionError("Active provider-patient relationship is required at publish time")

    published_at = datetime.now(timezone.utc)
    payload = {
        "actor_id": provider.id,
        "patient_id": plan.patient_id,
        "care_plan_id": plan.id,
        "title": plan.title,
        "diagnosis": plan.diagnosis,
        "advisories": [
            {
                "advisory_id": advisory.id,
                "advisory_type": advisory.advisory_type,
                "term": advisory.term,
                "tag": advisory.tag,
                "configuration": serialize_advisory(advisory)["configuration"],
            }
            for advisory in plan.advisories
        ],
    }
    event = create_event(event_type="advisory.publish", source="mantrana_mitra", payload=payload)
    plan.status = "ACTIVE"
    for advisory in plan.advisories:
        advisory.status = "PUBLISHED"
        advisory.published_at = published_at
    outbound, route, _ = send_event(db, event, actor_user=provider, commit=False)
    db.commit()
    db.refresh(plan)
    dispatch_event(db, outbound.event_id)
    record_audit_event(
        db,
        action="care_plan.published",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "care_plan_id": plan.id,
            "patient_id": plan.patient_id,
            "event_id": event.event_id,
            "route": route.handler,
        },
    )
    return plan, event.event_id


def serialize_care_plan(plan: CarePlan):
    return {
        "id": plan.id,
        "patient": {"id": plan.patient.id, "full_name": plan.patient.full_name},
        "provider_id": plan.provider_id,
        "title": plan.title,
        "diagnosis": plan.diagnosis,
        "status": plan.status,
        "advisories": [serialize_advisory(advisory) for advisory in plan.advisories],
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
