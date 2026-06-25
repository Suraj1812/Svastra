from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.care import Advisory, CarePlan
from app.models.postoffice import TimelineEvent
from app.models.workflow import CareTask, ClinicalAlert
from app.postoffice.event_registry import registry_entry


SOURCE_LABELS = {
    "mantrana_mitra": "Provider App",
    "rogi_mitra": "Patient App",
    "sahay_mitra": "Caregiver App",
    "svastra_backend": "Svastra Backend",
    "schedule_engine": "Schedule Engine",
}


def _event_document(event: TimelineEvent):
    try:
        document = json.loads(event.payload_json)
    except (TypeError, json.JSONDecodeError):
        return {}
    return document if isinstance(document, dict) else {}


def event_body(event: TimelineEvent):
    document = _event_document(event)
    body = document.get("body") or document.get("payload") or {}
    return body if isinstance(body, dict) else {}


def canonical_cep(event: TimelineEvent):
    document = _event_document(event)
    header = document.get("header")
    context = document.get("context")
    body = document.get("body")
    if isinstance(header, dict) and isinstance(context, dict) and isinstance(body, dict):
        return {"header": header, "context": context, "body": body}
    payload = event_body(event)
    return {
        "header": {
            "event_id": event.event_id,
            "event_type": registry_entry(event.event_type).canonical_type,
            "internal_event_type": event.event_type,
            "timestamp": event.occurred_at.isoformat(),
            "source": event.source_app,
        },
        "context": {
            "patient_id": event.patient_id,
            "actor_id": event.actor_id,
            "provider_id": event.provider_id,
            "episode_id": event.episode_id,
            "encounter_id": event.encounter_id,
            "target_app": event.target_app,
        },
        "body": payload,
    }


def _advisory(db: Session, advisory_id: Any):
    if not isinstance(advisory_id, int):
        return None
    return db.query(Advisory).filter(Advisory.id == advisory_id).first()


def _care_plan(db: Session, care_plan_id: Any):
    if not isinstance(care_plan_id, int):
        return None
    return db.query(CarePlan).filter(CarePlan.id == care_plan_id).first()


def _task(db: Session, task_uid: Any):
    if not isinstance(task_uid, str):
        return None
    return db.query(CareTask).filter(CareTask.task_uid == task_uid).first()


def _alert(db: Session, alert_uid: Any):
    if not isinstance(alert_uid, str):
        return None
    return db.query(ClinicalAlert).filter(ClinicalAlert.alert_uid == alert_uid).first()


def _value_label(body: dict):
    response = body.get("response")
    if not isinstance(response, dict):
        return None
    value = response.get("numeric_value")
    unit = response.get("measurement_unit")
    if value is None:
        return None
    return f"{value} {unit}".strip() if unit else str(value)


def _response_label(term: str, response_type: str, response_status: str, role: str):
    if response_type == "measurement":
        return f"{term} Submitted" if role == "patient" else f"{term} Received"
    if response_type == "investigation":
        return f"{term} Uploaded"
    if response_type == "recommendation":
        return f"{term} Completed" if response_status == "done" else f"{term} Missed"
    if response_type == "medication":
        return f"{term} Taken" if response_status == "taken" else f"{term} Missed"
    return f"{term} Response"


def _timeline_label_and_details(db: Session, event: TimelineEvent, role: str):
    body = event_body(event)
    entry = registry_entry(event.event_type)
    details: dict[str, Any] = {
        "Event Type": entry.canonical_type,
        "Source": SOURCE_LABELS.get(event.source_app, event.source_app),
    }

    if event.event_type == "advisory.publish":
        plan = _care_plan(db, body.get("care_plan_id"))
        diagnosis = body.get("diagnosis")
        details.update(
            {
                "Care Plan": body.get("title") or (plan.title if plan else None),
                "Diagnosis": diagnosis.get("term") if isinstance(diagnosis, dict) else diagnosis,
                "Advice Count": len(body.get("advisories") or []),
            }
        )
        return ("Care Plan Received" if role == "patient" else "Advisory Published"), details

    if event.event_type == "schedule.generate":
        advisory = _advisory(db, body.get("advisory_id"))
        details.update(
            {
                "Advice": advisory.term if advisory else None,
                "Tasks": body.get("task_count"),
                "First Due": body.get("first_due_at"),
                "Last Due": body.get("last_due_at"),
            }
        )
        return "Schedule Generated", details

    if event.event_type == "task.generate":
        advisory = _advisory(db, body.get("advisory_id"))
        task_ids = body.get("task_ids") if isinstance(body.get("task_ids"), list) else []
        details.update(
            {
                "Advice": advisory.term if advisory else None,
                "Tasks Delivered": len(task_ids),
                "Status": body.get("execution_status"),
            }
        )
        return "Care Plan Delivered", details

    if event.event_type == "response.log":
        advisory = _advisory(db, body.get("advisory_id"))
        term = advisory.term if advisory else str(body.get("response_type", "Response")).title()
        details.update(
            {
                "Advice": term,
                "Response": body.get("response_status"),
                "Status": body.get("execution_status"),
                "Recorded Value": _value_label(body),
            }
        )
        return _response_label(
            term,
            str(body.get("response_type") or ""),
            str(body.get("response_status") or ""),
            role,
        ), details

    if event.event_type == "attachment.upload":
        advisory = _advisory(db, body.get("advisory_id"))
        term = advisory.term if advisory else "Report"
        details.update(
            {
                "Investigation": term,
                "File": body.get("filename"),
                "Content Type": body.get("content_type"),
                "SHA-256": body.get("sha256"),
                "Status": body.get("execution_status"),
            }
        )
        return f"{term} Uploaded", details

    if event.event_type == "alert.trigger":
        alert = _alert(db, body.get("alert_id"))
        concept = body.get("concept") or (alert.advisory.term if alert else "Clinical")
        reason = body.get("reason")
        if reason == "threshold_exceeded":
            label = f"{concept} Above Threshold"
        elif reason == "non_response":
            label = f"{concept} Response Overdue"
        elif reason == "allergy_conflict":
            label = "Allergy Conflict"
        else:
            label = "Alert Triggered"
        details.update(
            {
                "Reason": reason,
                "Concept": concept,
                "Recorded Value": body.get("recorded_value"),
                "Severity": body.get("severity"),
                "Status": alert.status if alert else None,
                "Message": body.get("message"),
            }
        )
        return label, details

    if event.event_type in {"alert.acknowledge", "alert.resolve"}:
        alert = _alert(db, body.get("alert_id"))
        concept = body.get("concept") or (alert.advisory.term if alert else "Clinical")
        label = "Alert Acknowledged" if event.event_type == "alert.acknowledge" else "Alert Resolved"
        details.update(
            {
                "Alert": concept,
                "Previous Status": body.get("previous_status"),
                "Status": body.get("status"),
                "Reason": body.get("reason"),
                "Recorded Value": body.get("recorded_value"),
            }
        )
        return label, details

    details["Details"] = body
    return entry.label, details


def serialize_timeline_event(db: Session, event: TimelineEvent, *, role: str):
    entry = registry_entry(event.event_type)
    label, details = _timeline_label_and_details(db, event, role)
    return {
        "event_id": event.event_id,
        "event_type": entry.canonical_type,
        "internal_event_type": event.event_type,
        "label": label,
        "timestamp": event.occurred_at,
        "source": event.source_app,
        "source_label": SOURCE_LABELS.get(event.source_app, event.source_app),
        "patient_id": event.patient_id,
        "provider_id": event.provider_id,
        "episode_id": event.episode_id,
        "encounter_id": event.encounter_id,
        "details": {key: value for key, value in details.items() if value is not None},
        "cep": canonical_cep(event),
    }
