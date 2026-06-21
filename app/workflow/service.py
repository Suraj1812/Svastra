from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.audit.audit_service import record_audit_event
from app.config import settings
from app.models.care import Advisory, CarePlan
from app.models.consent import RelationshipConsent
from app.models.relationship import ProviderPatientLink
from app.models.user import User
from app.models.workflow import CareTask, ClinicalAlert, ClinicalAttachment, TaskResponse
from app.postoffice.dispatcher import (
    acknowledge_event,
    create_event,
    dispatch_event,
    send_event,
    serialize_acknowledgement,
)
from app.relationships.relationship_validator import has_active_provider_relationship
from app.terminology.term_service import resolve_response_reason


MAX_TASKS_PER_ADVISORY = 500
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
}


class ClinicalSafetyError(ValueError):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


def _configuration(advisory: Advisory):
    try:
        value = json.loads(advisory.configuration_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Stored advisory configuration is invalid") from error
    if not isinstance(value, dict):
        raise ValueError("Stored advisory configuration must be an object")
    return value


def _delivery_result(db: Session, event, *, actor: User):
    outbound = dispatch_event(db, event.event_id)
    acknowledgement, _ = acknowledge_event(
        db,
        event_id=event.event_id,
        received_by=outbound.target_app,
        status="received",
        actor_user=actor,
    )
    return {
        "event_id": event.event_id,
        "acknowledgement": serialize_acknowledgement(acknowledgement),
    }


def _new_alert(
    db: Session,
    *,
    advisory: Advisory,
    task: CareTask | None,
    alert_type: str,
    severity: str,
    message: str,
    notification_mode: str = "immediate",
):
    alert = ClinicalAlert(
        alert_uid=f"alert_{uuid4().hex}",
        advisory_id=advisory.id,
        task_id=task.id if task else None,
        provider_id=advisory.provider_id,
        patient_id=advisory.patient_id,
        alert_type=alert_type,
        severity=severity,
        message=message[:500],
        notification_mode=notification_mode,
        status="OPEN",
    )
    db.add(alert)
    db.flush()
    return alert


def _alert_event(alert: ClinicalAlert, *, actor: User):
    event = create_event(
        event_type="alert.trigger",
        source={"provider": "mantrana_mitra", "patient": "rogi_mitra"}[actor.role],
        payload={
            "actor_id": actor.id,
            "patient_id": alert.patient_id,
            "alert_id": alert.alert_uid,
            "advisory_id": alert.advisory_id,
            "task_id": alert.task.task_uid if alert.task else None,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "notification_mode": alert.notification_mode,
        },
    )
    alert.event_id = event.event_id
    return event


def enforce_prepublication_safety(
    db: Session,
    *,
    advisory: Advisory,
    provider: User,
    ip_address: str | None = None,
):
    warnings = _configuration(advisory).get("allergy_warnings") or []
    if not warnings:
        return
    existing = db.query(ClinicalAlert).filter(
        ClinicalAlert.advisory_id == advisory.id,
        ClinicalAlert.alert_type == "allergy_conflict",
        ClinicalAlert.status == "OPEN",
    ).first()
    if existing is not None:
        raise ClinicalSafetyError(existing.message)
    warning = warnings[0]
    alert = _new_alert(
        db,
        advisory=advisory,
        task=None,
        alert_type="allergy_conflict",
        severity="critical",
        message=(
            f"Publishing blocked: {advisory.term} conflicts with recorded allergy "
            f"{warning.get('allergen', 'unknown')}"
        ),
    )
    event = _alert_event(alert, actor=provider)
    db.flush()
    send_event(db, event, actor_user=provider, commit=False)
    db.commit()
    delivery = _delivery_result(db, event, actor=provider)
    record_audit_event(
        db,
        action="advisory.publication_blocked_allergy",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "advisory_id": advisory.id,
            "patient_id": advisory.patient_id,
            "alert_id": alert.alert_uid,
            "event_id": delivery["event_id"],
        },
    )
    raise ClinicalSafetyError(alert.message)


def _duration_hours(configuration: dict):
    multipliers = {"hours": 1, "days": 24, "weeks": 168, "months": 720}
    return configuration["duration_value"] * multipliers[configuration["duration_unit"]]


def _task_count(configuration: dict):
    frequency = configuration["frequency"]
    if frequency == "as_needed":
        return 1, None
    interval_hours = {
        "once_daily": 24,
        "twice_daily": 12,
        "three_times_daily": 8,
        "four_times_daily": 6,
        "every_4_hours": 4,
        "every_6_hours": 6,
        "weekly": 168,
        "monthly": 720,
    }[frequency]
    total_hours = _duration_hours(configuration)
    count = max(1, (total_hours + interval_hours - 1) // interval_hours)
    if count > MAX_TASKS_PER_ADVISORY:
        raise ValueError(
            f"Advisory schedule would create {count} tasks; maximum is {MAX_TASKS_PER_ADVISORY}"
        )
    return int(count), interval_hours


def _grace_delta(configuration: dict, advisory_type: str):
    if advisory_type == "investigation":
        value = int(configuration.get("grace_period_value", 2))
        unit = configuration.get("grace_period_unit", "days")
        return timedelta(hours=value if unit == "hours" else value * 24)
    warning = configuration.get("non_response_warning") or {}
    return timedelta(minutes=int(warning.get("clinical_grace_minutes", 60)))


def create_scheduled_tasks(
    db: Session,
    *,
    plan: CarePlan,
    advisory: Advisory,
    published_at: datetime,
):
    existing = db.query(CareTask).filter(CareTask.advisory_id == advisory.id).first()
    if existing is not None:
        raise ValueError("Schedule already exists for this advisory")
    configuration = _configuration(advisory)
    grace = _grace_delta(configuration, advisory.advisory_type)
    if advisory.advisory_type == "investigation":
        raw_due_date = configuration.get("due_date")
        due_date = date.fromisoformat(raw_due_date) if raw_due_date else published_at.date()
        due_times = [datetime.combine(due_date, time(hour=17), tzinfo=timezone.utc)]
    else:
        count, interval_hours = _task_count(configuration)
        due_times = [
            published_at + timedelta(hours=(interval_hours or 0) * index)
            for index in range(count)
        ]
    if advisory.advisory_type == "medication":
        dose_value = configuration.get("dose_value")
        if isinstance(dose_value, float) and dose_value.is_integer():
            dose_value = int(dose_value)
        dose = f"{dose_value} {configuration.get('dose_unit')}"
        title = f"Take {advisory.term} — {dose}, {configuration.get('route')}"
    elif advisory.advisory_type == "measurement":
        title = f"Record {advisory.term} ({configuration.get('measurement_unit')})"
    elif advisory.advisory_type == "investigation":
        title = f"Upload {advisory.term} report"
    else:
        title = advisory.term
    additional = configuration.get("additional_instructions")
    if additional:
        title = f"{title} — {additional}"
    expected = {
        "medication": "taken_or_missed",
        "measurement": "numeric_value",
        "recommendation": "done_or_missed",
        "investigation": "report_upload",
    }[advisory.advisory_type]
    tasks = []
    for index, due_at in enumerate(due_times, start=1):
        task = CareTask(
            task_uid=f"task_{uuid4().hex}",
            advisory_id=advisory.id,
            care_plan_id=plan.id,
            provider_id=advisory.provider_id,
            patient_id=advisory.patient_id,
            task_type=advisory.advisory_type,
            title=title[:255],
            expected_response=expected,
            ordinal=index,
            due_at=due_at,
            grace_expires_at=due_at + grace,
            execution_status="pending",
        )
        db.add(task)
        tasks.append(task)
    db.flush()
    return tasks


def create_publication_workflow_events(
    db: Session,
    *,
    plan: CarePlan,
    advisory: Advisory,
    tasks: list[CareTask],
    provider: User,
    advisory_payload: dict,
):
    schedule_event = create_event(
        event_type="schedule.generate",
        source="mantrana_mitra",
        payload={
            "actor_id": provider.id,
            "patient_id": plan.patient_id,
            "care_plan_id": plan.id,
            "advisory_id": advisory.id,
            "task_count": len(tasks),
            "first_due_at": tasks[0].due_at,
            "last_due_at": tasks[-1].due_at,
        },
    )
    publish_event = create_event(
        event_type="advisory.publish",
        source="mantrana_mitra",
        payload=advisory_payload,
    )
    task_event = create_event(
        event_type="task.generate",
        source="mantrana_mitra",
        payload={
            "actor_id": provider.id,
            "patient_id": plan.patient_id,
            "care_plan_id": plan.id,
            "advisory_id": advisory.id,
            "task_ids": [task.task_uid for task in tasks],
            "execution_status": "pending",
        },
    )
    for event in (schedule_event, publish_event, task_event):
        send_event(db, event, actor_user=provider, commit=False)
    return schedule_event, publish_event, task_event


def finish_publication_workflow(
    db: Session,
    *,
    events,
    provider: User,
    advisory: Advisory,
    task_count: int,
    ip_address: str | None = None,
):
    deliveries = [_delivery_result(db, event, actor=provider) for event in events]
    record_audit_event(
        db,
        action="schedule.generated",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "advisory_id": advisory.id,
            "patient_id": advisory.patient_id,
            "task_count": task_count,
            "event_id": events[0].event_id,
        },
    )
    record_audit_event(
        db,
        action="task.generated",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "advisory_id": advisory.id,
            "patient_id": advisory.patient_id,
            "task_count": task_count,
            "event_id": events[2].event_id,
        },
    )
    return {
        "schedule": deliveries[0],
        "advisory": deliveries[1],
        "tasks": deliveries[2],
    }


def serialize_task(task: CareTask):
    response = task.response
    return {
        "task_id": task.task_uid,
        "advisory_id": task.advisory_id,
        "care_plan_id": task.care_plan_id,
        "task_type": task.task_type,
        "patient": {"id": task.patient.id, "full_name": task.patient.full_name},
        "title": task.title,
        "advisory": task.advisory.term,
        "configuration": _configuration(task.advisory),
        "expected_response": task.expected_response,
        "due_at": task.due_at,
        "grace_expires_at": task.grace_expires_at,
        "execution_status": task.execution_status,
        "response": serialize_response(response) if response else None,
        "created_at": task.created_at,
    }


def serialize_response(response: TaskResponse):
    return {
        "response_id": response.response_uid,
        "response_status": response.response_status,
        "value": json.loads(response.response_value_json),
        "is_late": response.is_late,
        "responded_at": response.responded_at,
        "event_id": response.response_event_id,
        "attachment": serialize_attachment(response.attachment) if response.attachment else None,
    }


def serialize_attachment(attachment: ClinicalAttachment):
    return {
        "attachment_id": attachment.attachment_uid,
        "filename": attachment.original_filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "sha256": attachment.sha256,
        "uploaded_at": attachment.uploaded_at,
    }


def serialize_alert(alert: ClinicalAlert):
    return {
        "alert_id": alert.alert_uid,
        "advisory_id": alert.advisory_id,
        "task_id": alert.task.task_uid if alert.task else None,
        "patient": {"id": alert.patient.id, "full_name": alert.patient.full_name},
        "advisory": alert.advisory.term,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "notification_mode": alert.notification_mode,
        "status": alert.status,
        "event_id": alert.event_id,
        "acknowledged_at": alert.acknowledged_at,
        "created_at": alert.created_at,
    }


def get_patient_tasks(db: Session, *, patient_id: int, execution_status: str | None = None):
    query = db.query(CareTask).options(
        joinedload(CareTask.advisory),
        joinedload(CareTask.response).joinedload(TaskResponse.attachment),
    ).filter(CareTask.patient_id == patient_id)
    if execution_status:
        query = query.filter(CareTask.execution_status == execution_status)
    return query.order_by(CareTask.due_at.asc(), CareTask.id.asc()).limit(500).all()


def get_provider_tasks(
    db: Session,
    *,
    provider_id: int,
    patient_id: int | None = None,
    execution_status: str | None = None,
):
    query = db.query(CareTask).options(
        joinedload(CareTask.advisory),
        joinedload(CareTask.patient),
        joinedload(CareTask.response).joinedload(TaskResponse.attachment),
    ).join(
        ProviderPatientLink,
        (ProviderPatientLink.provider_id == CareTask.provider_id)
        & (ProviderPatientLink.patient_id == CareTask.patient_id),
    ).join(
        RelationshipConsent,
        RelationshipConsent.id == ProviderPatientLink.source_consent_id,
    ).filter(
        CareTask.provider_id == provider_id,
        ProviderPatientLink.status == "active",
        RelationshipConsent.status == "ACTIVE",
    )
    if patient_id:
        query = query.filter(CareTask.patient_id == patient_id)
    if execution_status:
        query = query.filter(CareTask.execution_status == execution_status)
    return query.order_by(CareTask.due_at.desc(), CareTask.id.desc()).limit(500).all()


def get_scoped_task(db: Session, *, task_uid: str, user: User):
    task = db.query(CareTask).options(
        joinedload(CareTask.advisory),
        joinedload(CareTask.response).joinedload(TaskResponse.attachment),
    ).filter(CareTask.task_uid == task_uid).first()
    if task is None:
        raise ValueError("Task not found")
    if user.role == "patient" and task.patient_id == user.id:
        return task
    if user.role == "provider" and task.provider_id == user.id and has_active_provider_relationship(
        db, provider_id=user.id, patient_id=task.patient_id
    ):
        return task
    raise PermissionError("Task is outside the user's consent-backed scope")


def _response_value(
    db: Session,
    *,
    task: CareTask,
    response_status: str,
    reason: dict | None,
    numeric_value: float | None,
    measurement_unit: str | None,
):
    configuration = _configuration(task.advisory)
    allowed = {
        "medication": {"taken", "missed"},
        "measurement": {"recorded"},
        "recommendation": {"done", "missed"},
        "investigation": {"missed"},
    }[task.task_type]
    if response_status not in allowed:
        raise ValueError(f"{task.task_type} tasks accept: {', '.join(sorted(allowed))}")
    if task.task_type == "medication" and response_status == "missed" and reason is None:
        raise ValueError("Select a coded reason when medication is missed")
    resolved_reason = None
    if reason is not None:
        resolved_reason = resolve_response_reason(
            db,
            concept_id=reason["concept_id"],
            term=reason["term"],
        )
    if task.task_type == "measurement":
        if numeric_value is None or measurement_unit is None:
            raise ValueError("Measurement response requires a numeric value and unit")
        if measurement_unit != configuration["measurement_unit"]:
            raise ValueError("Response unit must match the advisory measurement unit")
    elif numeric_value is not None or measurement_unit is not None:
        raise ValueError("Numeric values are accepted only for measurement tasks")
    return {
        "reason": resolved_reason,
        "numeric_value": numeric_value,
        "measurement_unit": measurement_unit,
    }


def _aggregate_advisory_status(db: Session, advisory: Advisory):
    tasks = db.query(CareTask).filter(CareTask.advisory_id == advisory.id).all()
    if not tasks or any(task.execution_status == "pending" for task in tasks):
        advisory.execution_status = "pending"
    elif any(task.execution_status == "missed" for task in tasks):
        advisory.execution_status = "missed"
    elif any(task.execution_status == "completed_late" for task in tasks):
        advisory.execution_status = "completed_late"
    else:
        advisory.execution_status = "completed"


def _threshold_breached(configuration: dict, value: float):
    rule = configuration.get("value_warning")
    if not rule:
        return False
    threshold = rule["threshold_value"]
    return {
        "more_than": value > threshold,
        "less_than": value < threshold,
        "at_least": value >= threshold,
        "at_most": value <= threshold,
        "equal_to": value == threshold,
    }[rule["condition"]]


def record_task_response(
    db: Session,
    *,
    task_uid: str,
    patient: User,
    response_status: str,
    reason: dict | None,
    numeric_value: float | None,
    measurement_unit: str | None,
    ip_address: str | None = None,
):
    task = get_scoped_task(db, task_uid=task_uid, user=patient)
    if patient.role != "patient" or task.patient_id != patient.id:
        raise PermissionError("Only the assigned patient may respond to this task")
    if task.execution_status != "pending" or task.response is not None:
        raise ValueError("Task already has an immutable response")
    response_value = _response_value(
        db,
        task=task,
        response_status=response_status,
        reason=reason,
        numeric_value=numeric_value,
        measurement_unit=measurement_unit,
    )
    responded_at = _utcnow()
    is_late = responded_at > task.grace_expires_at.replace(tzinfo=timezone.utc)
    execution_status = (
        "missed"
        if response_status == "missed"
        else "completed_late" if is_late else "completed"
    )
    response = TaskResponse(
        response_uid=f"resp_{uuid4().hex}",
        task_id=task.id,
        advisory_id=task.advisory_id,
        patient_id=patient.id,
        response_status=response_status,
        response_value_json=json.dumps(response_value, sort_keys=True),
        is_late=is_late,
        responded_at=responded_at,
    )
    db.add(response)
    task.execution_status = execution_status
    task.completed_at = responded_at
    db.flush()
    _aggregate_advisory_status(db, task.advisory)
    event = create_event(
        event_type="response.log",
        source="rogi_mitra",
        payload={
            "actor_id": patient.id,
            "patient_id": patient.id,
            "task_id": task.task_uid,
            "advisory_id": task.advisory_id,
            "response_type": task.task_type,
            "response_status": response_status,
            "response": response_value,
            "execution_status": execution_status,
        },
    )
    response.response_event_id = event.event_id
    db.flush()
    send_event(db, event, actor_user=patient, commit=False)
    events = [event]
    task_configuration = _configuration(task.advisory)
    value_rule = task_configuration.get("value_warning") or {}
    if (
        task.task_type == "measurement"
        and value_rule.get("notification") != "none"
        and _threshold_breached(task_configuration, numeric_value)
    ):
        alert = _new_alert(
            db,
            advisory=task.advisory,
            task=task,
            alert_type="value_threshold",
            severity="high",
            message=f"{task.advisory.term} value {numeric_value} {measurement_unit} crossed the configured threshold",
            notification_mode=value_rule.get("notification", "immediate"),
        )
        alert_event = _alert_event(alert, actor=patient)
        db.flush()
        send_event(db, alert_event, actor_user=patient, commit=False)
        events.append(alert_event)
    db.commit()
    deliveries = [_delivery_result(db, item, actor=patient) for item in events]
    record_audit_event(
        db,
        action="task.response_received",
        actor_user_id=patient.id,
        actor_role=patient.role,
        mobile_number=patient.mobile_number,
        ip_address=ip_address,
        metadata={
            "task_id": task.task_uid,
            "advisory_id": task.advisory_id,
            "response_id": response.response_uid,
            "response_status": response_status,
            "execution_status": execution_status,
            "event_id": event.event_id,
        },
    )
    db.refresh(task)
    db.refresh(response)
    return task, response, deliveries


def _validated_attachment(filename: str, content_type: str, content: bytes):
    safe_name = Path(filename or "").name.strip()
    if not safe_name or len(safe_name) > 180 or "\x00" in safe_name:
        raise ValueError("Attachment filename must contain 1 to 180 safe characters")
    expected = ALLOWED_ATTACHMENT_TYPES.get(content_type)
    if expected is None:
        raise ValueError("Only PDF and JPEG investigation reports are accepted")
    magic, extension = expected
    if not content.startswith(magic):
        raise ValueError("Attachment content does not match its declared file type")
    if not content or len(content) > settings.attachment_max_bytes:
        raise ValueError(
            f"Attachment must be between 1 and {settings.attachment_max_bytes} bytes"
        )
    if not safe_name.lower().endswith((".pdf", ".jpg", ".jpeg")):
        raise ValueError("Attachment filename extension must be PDF, JPG, or JPEG")
    return safe_name, extension


def upload_investigation_report(
    db: Session,
    *,
    task_uid: str,
    patient: User,
    filename: str,
    content_type: str,
    content: bytes,
    ip_address: str | None = None,
):
    task = get_scoped_task(db, task_uid=task_uid, user=patient)
    if patient.role != "patient" or task.patient_id != patient.id:
        raise PermissionError("Only the assigned patient may upload this report")
    if task.task_type != "investigation":
        raise ValueError("Report uploads are accepted only for investigation tasks")
    if task.execution_status != "pending" or task.response is not None or task.attachment is not None:
        raise ValueError("Task already has an immutable response or attachment")
    safe_name, extension = _validated_attachment(filename, content_type, content)
    uploaded_at = _utcnow()
    is_late = uploaded_at > task.grace_expires_at.replace(tzinfo=timezone.utc)
    execution_status = "completed_late" if is_late else "completed"
    attachment_uid = f"attachment_{uuid4().hex}"
    storage_root = settings.attachment_storage_path.resolve()
    storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    storage_path = storage_root / f"{attachment_uid}{extension}"
    if storage_root not in storage_path.resolve().parents:
        raise ValueError("Attachment storage path is invalid")
    with open(storage_path, "xb") as handle:
        os.chmod(storage_path, 0o600)
        handle.write(content)
    response = TaskResponse(
        response_uid=f"resp_{uuid4().hex}",
        task_id=task.id,
        advisory_id=task.advisory_id,
        patient_id=patient.id,
        response_status="uploaded",
        response_value_json=json.dumps({"attachment_id": attachment_uid}, sort_keys=True),
        is_late=is_late,
        responded_at=uploaded_at,
    )
    db.add(response)
    db.flush()
    attachment = ClinicalAttachment(
        attachment_uid=attachment_uid,
        task_id=task.id,
        response_id=response.id,
        patient_id=patient.id,
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        storage_path=str(storage_path),
        uploaded_at=uploaded_at,
    )
    db.add(attachment)
    task.execution_status = execution_status
    task.completed_at = uploaded_at
    db.flush()
    _aggregate_advisory_status(db, task.advisory)
    event = create_event(
        event_type="response.log",
        source="rogi_mitra",
        payload={
            "actor_id": patient.id,
            "patient_id": patient.id,
            "task_id": task.task_uid,
            "advisory_id": task.advisory_id,
            "response_type": "investigation",
            "response_status": "uploaded",
            "attachment": {
                "attachment_id": attachment_uid,
                "filename": safe_name,
                "content_type": content_type,
                "size_bytes": len(content),
                "sha256": attachment.sha256,
            },
            "execution_status": execution_status,
        },
    )
    response.response_event_id = event.event_id
    db.flush()
    try:
        send_event(db, event, actor_user=patient, commit=False)
        db.commit()
    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    delivery = _delivery_result(db, event, actor=patient)
    record_audit_event(
        db,
        action="investigation.report_uploaded",
        actor_user_id=patient.id,
        actor_role=patient.role,
        mobile_number=patient.mobile_number,
        ip_address=ip_address,
        metadata={
            "task_id": task.task_uid,
            "attachment_id": attachment_uid,
            "sha256": attachment.sha256,
            "size_bytes": len(content),
            "event_id": event.event_id,
        },
    )
    db.refresh(task)
    db.refresh(response)
    db.refresh(attachment)
    return task, response, attachment, delivery


def evaluate_overdue_tasks(
    db: Session,
    *,
    provider: User,
    patient_id: int | None = None,
    ip_address: str | None = None,
):
    if provider.role != "provider":
        raise PermissionError("Provider role is required")
    if patient_id and not has_active_provider_relationship(
        db, provider_id=provider.id, patient_id=patient_id
    ):
        raise PermissionError("Active provider-patient relationship is required")
    query = db.query(CareTask).options(joinedload(CareTask.advisory)).join(
        ProviderPatientLink,
        (ProviderPatientLink.provider_id == CareTask.provider_id)
        & (ProviderPatientLink.patient_id == CareTask.patient_id),
    ).join(
        RelationshipConsent,
        RelationshipConsent.id == ProviderPatientLink.source_consent_id,
    ).filter(
        CareTask.provider_id == provider.id,
        CareTask.execution_status == "pending",
        CareTask.grace_expires_at < _utcnow(),
        ProviderPatientLink.status == "active",
        RelationshipConsent.status == "ACTIVE",
    )
    if patient_id:
        query = query.filter(CareTask.patient_id == patient_id)
    tasks = query.order_by(CareTask.grace_expires_at).limit(500).all()
    events = []
    alerts = []
    touched_advisories = set()
    for task in tasks:
        task.execution_status = "missed"
        task.completed_at = _utcnow()
        touched_advisories.add(task.advisory_id)
        configuration = _configuration(task.advisory)
        notification_mode = "immediate"
        should_alert = (
            configuration.get("alert_if_not_uploaded", False)
            if task.task_type == "investigation"
            else bool(configuration.get("non_response_warning"))
        )
        if task.task_type != "investigation":
            notification_mode = (configuration.get("non_response_warning") or {}).get(
                "notification", "immediate"
            )
            should_alert = should_alert and notification_mode != "none"
        if should_alert:
            alert = _new_alert(
                db,
                advisory=task.advisory,
                task=task,
                alert_type="non_response",
                severity="high" if task.task_type == "investigation" else "medium",
                message=f"No response received for {task.advisory.term} before the clinical grace period expired",
                notification_mode=notification_mode,
            )
            event = _alert_event(alert, actor=provider)
            db.flush()
            send_event(db, event, actor_user=provider, commit=False)
            alerts.append(alert)
            events.append(event)
    db.flush()
    for advisory_id in touched_advisories:
        advisory = db.query(Advisory).filter(Advisory.id == advisory_id).one()
        _aggregate_advisory_status(db, advisory)
    db.commit()
    deliveries = [_delivery_result(db, event, actor=provider) for event in events]
    for task in tasks:
        record_audit_event(
            db,
            action="task.missed",
            actor_user_id=provider.id,
            actor_role=provider.role,
            mobile_number=provider.mobile_number,
            ip_address=ip_address,
            metadata={"task_id": task.task_uid, "patient_id": task.patient_id},
        )
    return tasks, alerts, deliveries


def get_provider_alerts(
    db: Session,
    *,
    provider_id: int,
    patient_id: int | None = None,
    status: str | None = None,
):
    query = db.query(ClinicalAlert).options(
        joinedload(ClinicalAlert.patient),
        joinedload(ClinicalAlert.advisory),
        joinedload(ClinicalAlert.task),
    ).join(
        ProviderPatientLink,
        (ProviderPatientLink.provider_id == ClinicalAlert.provider_id)
        & (ProviderPatientLink.patient_id == ClinicalAlert.patient_id),
    ).join(
        RelationshipConsent,
        RelationshipConsent.id == ProviderPatientLink.source_consent_id,
    ).filter(
        ClinicalAlert.provider_id == provider_id,
        ProviderPatientLink.status == "active",
        RelationshipConsent.status == "ACTIVE",
    )
    if patient_id:
        query = query.filter(ClinicalAlert.patient_id == patient_id)
    if status:
        query = query.filter(ClinicalAlert.status == status)
    return query.order_by(ClinicalAlert.created_at.desc()).limit(500).all()


def acknowledge_alert(
    db: Session,
    *,
    alert_uid: str,
    provider: User,
    ip_address: str | None = None,
):
    alert = db.query(ClinicalAlert).filter(ClinicalAlert.alert_uid == alert_uid).first()
    if alert is None:
        raise ValueError("Alert not found")
    if provider.role != "provider" or alert.provider_id != provider.id:
        raise PermissionError("Only the owning provider may acknowledge this alert")
    if not has_active_provider_relationship(
        db, provider_id=provider.id, patient_id=alert.patient_id
    ):
        raise PermissionError("Active provider-patient relationship is required")
    if alert.status == "ACKNOWLEDGED":
        return alert, False
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = _utcnow()
    db.commit()
    db.refresh(alert)
    record_audit_event(
        db,
        action="alert.acknowledged",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={"alert_id": alert.alert_uid, "patient_id": alert.patient_id},
    )
    return alert, True


def get_scoped_attachment(db: Session, *, attachment_uid: str, user: User):
    attachment = db.query(ClinicalAttachment).options(
        joinedload(ClinicalAttachment.task),
    ).filter(ClinicalAttachment.attachment_uid == attachment_uid).first()
    if attachment is None:
        raise ValueError("Attachment not found")
    task = attachment.task
    if user.role == "patient" and attachment.patient_id == user.id:
        return attachment
    if user.role == "provider" and task.provider_id == user.id and has_active_provider_relationship(
        db, provider_id=user.id, patient_id=attachment.patient_id
    ):
        return attachment
    raise PermissionError("Attachment is outside the user's consent-backed scope")
