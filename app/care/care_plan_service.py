from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.audit.audit_service import record_audit_event
from app.care.advisory_service import serialize_advisory
from app.care.diagnosis import diagnosis_columns, serialize_diagnosis
from app.models.care import Advisory, CarePlan
from app.models.user import User
from app.relationships.relationship_validator import has_active_provider_relationship
from app.workflow.service import (
    create_publication_workflow_events,
    create_scheduled_tasks,
    enforce_prepublication_safety,
    finish_publication_workflow,
)


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
    diagnosis: Any = None,
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
    normalized_diagnosis = diagnosis_columns(diagnosis)
    plan = CarePlan(
        provider_id=provider.id,
        patient_id=patient_id,
        title=title,
        **normalized_diagnosis,
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


def update_care_plan(
    db: Session,
    *,
    care_plan_id: int,
    provider: User,
    title: str,
    diagnosis: Any,
    ip_address: str | None = None,
):
    plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=provider)
    if plan.is_archived:
        raise ValueError("Archived care plans cannot be updated")
    normalized_diagnosis = diagnosis_columns(diagnosis)
    plan.title = title
    plan.diagnosis = normalized_diagnosis["diagnosis"]
    plan.diagnosis_concept_id = normalized_diagnosis["diagnosis_concept_id"]
    plan.diagnosis_term = normalized_diagnosis["diagnosis_term"]
    plan.diagnosis_notes = normalized_diagnosis["diagnosis_notes"]
    db.commit()
    db.refresh(plan)
    record_audit_event(
        db,
        action="care_plan.updated",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={"care_plan_id": plan.id, "patient_id": plan.patient_id},
    )
    return plan


def archive_care_plan(
    db: Session,
    *,
    care_plan_id: int,
    provider: User,
    ip_address: str | None = None,
):
    plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=provider)
    if plan.is_archived:
        return plan, False
    plan.is_archived = True
    plan.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    record_audit_event(
        db,
        action="care_plan.archived",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={"care_plan_id": plan.id, "patient_id": plan.patient_id},
    )
    return plan, True


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


def _advisory_publish_payload(plan: CarePlan, advisory: Advisory, provider: User):
    return {
        "actor_id": provider.id,
        "patient_id": plan.patient_id,
        "care_plan_id": plan.id,
        "title": plan.title,
        "diagnosis": serialize_diagnosis(plan),
        "execution_status": advisory.execution_status,
        "advisories": [
            {
                "advisory_id": advisory.id,
                "advisory_type": advisory.advisory_type,
                "concept_id": advisory.concept_id,
                "term": advisory.term,
                "tag": advisory.tag,
                "execution_status": advisory.execution_status,
                "configuration": serialize_advisory(advisory)["configuration"],
            }
        ],
    }


def publish_advisory(
    db: Session,
    *,
    care_plan_id: int,
    advisory_id: int,
    provider: User,
    ip_address: str | None = None,
):
    plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=provider)
    if plan.is_archived:
        raise ValueError("Archived care plans cannot publish advisories")
    advisory = next((item for item in plan.advisories if item.id == advisory_id), None)
    if advisory is None:
        raise ValueError("Advisory not found in this care plan")
    if advisory.status != "DRAFT":
        raise ValueError("Advisory is already published and immutable")
    if not has_active_provider_relationship(
        db,
        provider_id=provider.id,
        patient_id=plan.patient_id,
    ):
        raise PermissionError("Active provider-patient relationship is required at publish time")

    enforce_prepublication_safety(
        db,
        advisory=advisory,
        provider=provider,
        ip_address=ip_address,
    )
    published_at = datetime.now(timezone.utc)
    plan.status = "ACTIVE"
    advisory.status = "PUBLISHED"
    advisory.published_at = published_at
    tasks = create_scheduled_tasks(
        db,
        plan=plan,
        advisory=advisory,
        published_at=published_at,
    )
    events = create_publication_workflow_events(
        db,
        plan=plan,
        advisory=advisory,
        tasks=tasks,
        provider=provider,
        advisory_payload=_advisory_publish_payload(plan, advisory, provider),
    )
    db.commit()
    workflow = finish_publication_workflow(
        db,
        events=events,
        provider=provider,
        advisory=advisory,
        task_count=len(tasks),
        ip_address=ip_address,
    )
    acknowledgement = workflow["advisory"]["acknowledgement"]
    record_audit_event(
        db,
        action="advisory.published",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "care_plan_id": plan.id,
            "advisory_id": advisory.id,
            "patient_id": plan.patient_id,
            "event_id": events[1].event_id,
            "ack_id": acknowledgement["ack_id"],
            "task_count": len(tasks),
        },
    )
    return advisory, events[1].event_id, acknowledgement, workflow


def publish_care_plan(
    db: Session,
    *,
    care_plan_id: int,
    provider: User,
    ip_address: str | None = None,
):
    plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=provider)
    if plan.is_archived:
        raise ValueError("Archived care plans cannot be published")
    draft_advisories = [item for item in plan.advisories if item.status == "DRAFT"]
    if not draft_advisories:
        raise ValueError("Add at least one valid advisory before publishing")
    if not has_active_provider_relationship(
        db,
        provider_id=provider.id,
        patient_id=plan.patient_id,
    ):
        raise PermissionError("Active provider-patient relationship is required at publish time")

    for advisory in draft_advisories:
        enforce_prepublication_safety(
            db,
            advisory=advisory,
            provider=provider,
            ip_address=ip_address,
        )

    deliveries = []
    for advisory in draft_advisories:
        _, event_id, acknowledgement, workflow = publish_advisory(
            db,
            care_plan_id=plan.id,
            advisory_id=advisory.id,
            provider=provider,
            ip_address=ip_address,
        )
        deliveries.append(
            {
                "event_id": event_id,
                "acknowledgement": acknowledgement,
                "workflow": workflow,
            }
        )
    db.refresh(plan)
    return plan, deliveries


def serialize_care_plan(plan: CarePlan):
    return {
        "id": plan.id,
        "patient": {"id": plan.patient.id, "full_name": plan.patient.full_name},
        "provider_id": plan.provider_id,
        "title": plan.title,
        "diagnosis": serialize_diagnosis(plan),
        "status": "INACTIVE" if plan.is_archived else plan.status,
        "archived_at": plan.archived_at,
        "advisories": [serialize_advisory(advisory) for advisory in plan.advisories],
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
