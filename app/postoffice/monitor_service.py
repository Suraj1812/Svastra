from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.postoffice import (
    OutboundEvent,
    PostOfficeAcknowledgement,
    ReceivedEvent,
    TimelineEvent,
)
from app.schemas.monitor import EventMonitorFilters, EventMonitorQuery


class MonitorValidationError(ValueError):
    pass


_ALWAYS_REDACT = {
    "abha_number",
    "emergency_contact_mobile",
    "ip_address",
    "mobile_number",
    "otp",
    "session_id",
    "session_token",
}
_CAREGIVER_REDACT = {
    "advisories",
    "configuration",
    "diagnosis",
    "message_text",
}
_PREVIEW_KEYS = {
    "alert_id",
    "care_plan_id",
    "consent_id",
    "consent_type",
    "message_id",
    "new_state",
    "previous_state",
    "relationship_id",
    "relationship_type",
    "response_type",
    "severity",
    "status",
    "task_id",
}


def _delivery_status(outbound: OutboundEvent | None, acknowledgement: PostOfficeAcknowledgement | None):
    if acknowledgement is not None:
        return "acknowledged"
    if outbound is not None:
        return outbound.status
    return "untracked"


def _status_expression():
    return case(
        (PostOfficeAcknowledgement.id.is_not(None), "acknowledged"),
        (OutboundEvent.id.is_not(None), OutboundEvent.status),
        else_="untracked",
    )


def _joined_query(db: Session):
    return (
        db.query(TimelineEvent, OutboundEvent, PostOfficeAcknowledgement, ReceivedEvent)
        .outerjoin(OutboundEvent, OutboundEvent.event_id == TimelineEvent.event_id)
        .outerjoin(
            PostOfficeAcknowledgement,
            PostOfficeAcknowledgement.event_id == TimelineEvent.event_id,
        )
        .outerjoin(ReceivedEvent, ReceivedEvent.event_id == TimelineEvent.event_id)
    )


def _apply_filters(query, filters: EventMonitorFilters):
    query = query.filter(TimelineEvent.patient_id == filters.patient_id)
    if filters.event_type:
        query = query.filter(TimelineEvent.event_type == filters.event_type)
    if filters.delivery_status:
        query = query.filter(_status_expression() == filters.delivery_status)
    if filters.source:
        query = query.filter(TimelineEvent.source_app == filters.source)
    if filters.target:
        query = query.filter(TimelineEvent.target_app == filters.target)
    if filters.event_id_prefix:
        query = query.filter(TimelineEvent.event_id.startswith(filters.event_id_prefix))
    if filters.occurred_from:
        query = query.filter(TimelineEvent.occurred_at >= filters.occurred_from)
    if filters.occurred_to:
        query = query.filter(TimelineEvent.occurred_at <= filters.occurred_to)
    return query


def _apply_viewer_scope(query, *, role: str, viewer_id: int):
    if role == "patient":
        return query
    return query.filter(
        or_(
            TimelineEvent.related_user_id == viewer_id,
            TimelineEvent.actor_id == str(viewer_id),
        )
    )


def _filter_fingerprint(filters: EventMonitorFilters):
    data = filters.model_dump(mode="json", exclude={"cursor", "limit"}, exclude_none=True)
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]


def _encode_cursor(event: TimelineEvent, filters: EventMonitorFilters):
    body = json.dumps(
        {
            "occurred_at": event.occurred_at.isoformat(),
            "id": event.id,
            "scope": _filter_fingerprint(filters),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")
    signature = hmac.new(
        settings.monitor_cursor_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _decode_cursor(cursor: str, filters: EventMonitorFilters):
    try:
        encoded, signature = cursor.split(".", 1)
        expected = hmac.new(
            settings.monitor_cursor_secret.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise MonitorValidationError("Monitor cursor signature is invalid")
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        if payload.get("scope") != _filter_fingerprint(filters):
            raise MonitorValidationError("Monitor cursor does not match the active filters")
        occurred_at = datetime.fromisoformat(payload["occurred_at"])
        event_id = int(payload["id"])
        if event_id <= 0:
            raise ValueError("invalid id")
        return occurred_at, event_id
    except MonitorValidationError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise MonitorValidationError("Monitor cursor is malformed or expired") from error


def _parse_payload(event: TimelineEvent):
    try:
        document = json.loads(event.payload_json)
        payload = document.get("payload")
        return payload if isinstance(payload, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _payload_integrity(event: TimelineEvent):
    actual = hashlib.sha256(event.payload_json.encode("utf-8")).hexdigest()
    if not event.payload_sha256:
        return "legacy_unverified", actual
    return ("verified" if hmac.compare_digest(actual, event.payload_sha256) else "mismatch"), actual


def _payload_preview(event: TimelineEvent):
    payload = _parse_payload(event)
    preview = {key: payload[key] for key in sorted(_PREVIEW_KEYS) if key in payload}
    advisories = payload.get("advisories")
    if isinstance(advisories, list):
        preview["advisory_count"] = len(advisories)
    return preview


def _redact_payload(value, *, role: str, redacted_fields: set[str], path: str = "payload"):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = key.lower()
            field_path = f"{path}.{key}"
            should_redact = (
                lowered in _ALWAYS_REDACT
                or "token" in lowered
                or (role == "caregiver" and lowered in _CAREGIVER_REDACT)
            )
            if should_redact:
                result[key] = "[REDACTED]"
                redacted_fields.add(field_path)
            else:
                result[key] = _redact_payload(
                    item,
                    role=role,
                    redacted_fields=redacted_fields,
                    path=field_path,
                )
        return result
    if isinstance(value, list):
        return [
            _redact_payload(item, role=role, redacted_fields=redacted_fields, path=f"{path}[]")
            for item in value
        ]
    return value


def _delivery_latency_ms(event: TimelineEvent, acknowledgement: PostOfficeAcknowledgement | None):
    if acknowledgement is None:
        return None
    started = event.created_at
    finished = acknowledgement.received_at
    if started is None or finished is None:
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    return max(0, round((finished - started).total_seconds() * 1000, 2))


def _anomalies(
    event: TimelineEvent,
    outbound: OutboundEvent | None,
    acknowledgement: PostOfficeAcknowledgement | None,
    received: ReceivedEvent | None,
    integrity_status: str,
):
    anomalies = []
    if integrity_status == "mismatch":
        anomalies.append("PAYLOAD_INTEGRITY_MISMATCH")
    if acknowledgement is not None and received is None:
        anomalies.append("ACK_WITHOUT_RECEIVER_COPY")
    if received is not None and acknowledgement is None:
        anomalies.append("RECEIVER_COPY_WITHOUT_ACK")
    if acknowledgement is not None and outbound is not None:
        anomalies.append("ACKNOWLEDGED_EVENT_STILL_QUEUED")
    if outbound is None and acknowledgement is None:
        anomalies.append("EVENT_WITHOUT_DELIVERY_RECORD")
    return anomalies


def _serialize_monitor_event(row, *, include_payload: bool = False, role: str = "patient"):
    event, outbound, acknowledgement, received = row
    integrity_status, calculated_digest = _payload_integrity(event)
    anomalies = _anomalies(event, outbound, acknowledgement, received, integrity_status)
    retry_count = (
        acknowledgement.retry_count
        if acknowledgement is not None
        else outbound.retry_count if outbound is not None else 0
    )
    last_attempt_at = (
        acknowledgement.last_attempt_at
        if acknowledgement is not None
        else outbound.last_attempt_at if outbound is not None else None
    )
    data = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "patient_id": event.patient_id,
        "actor_id": event.actor_id,
        "source": event.source_app,
        "target": event.target_app,
        "delivery_status": _delivery_status(outbound, acknowledgement),
        "retry_count": retry_count,
        "occurred_at": event.occurred_at,
        "recorded_at": event.created_at,
        "last_attempt_at": last_attempt_at,
        "acknowledged_at": acknowledgement.received_at if acknowledgement else None,
        "delivery_latency_ms": _delivery_latency_ms(event, acknowledgement),
        "ack_id": acknowledgement.ack_id if acknowledgement else None,
        "received_by": acknowledgement.received_by if acknowledgement else None,
        "integrity_status": integrity_status,
        "anomalies": anomalies,
        "payload_preview": _payload_preview(event),
    }
    if include_payload:
        redacted_fields: set[str] = set()
        data["payload"] = _redact_payload(
            _parse_payload(event),
            role=role,
            redacted_fields=redacted_fields,
        )
        data["redacted_fields"] = sorted(redacted_fields)
        data["payload_sha256"] = event.payload_sha256 or calculated_digest
        lifecycle = [
            {"state": "recorded", "timestamp": event.created_at},
        ]
        if last_attempt_at:
            lifecycle.append({"state": "sent", "timestamp": last_attempt_at})
        if received:
            lifecycle.append({"state": "received", "timestamp": received.received_at})
        if acknowledgement:
            lifecycle.append({"state": "acknowledged", "timestamp": acknowledgement.received_at})
        data["lifecycle"] = lifecycle
        data["last_error"] = (
            {
                "code": outbound.last_error_code,
                "message": outbound.last_error_message,
            }
            if outbound and (outbound.last_error_code or outbound.last_error_message)
            else None
        )
    return data


def list_monitor_events(db: Session, *, filters: EventMonitorQuery, role: str, viewer_id: int):
    query = _apply_viewer_scope(
        _apply_filters(_joined_query(db), filters),
        role=role,
        viewer_id=viewer_id,
    )
    if filters.cursor:
        cursor_time, cursor_id = _decode_cursor(filters.cursor, filters)
        query = query.filter(
            or_(
                TimelineEvent.occurred_at < cursor_time,
                and_(TimelineEvent.occurred_at == cursor_time, TimelineEvent.id < cursor_id),
            )
        )
    rows = query.order_by(TimelineEvent.occurred_at.desc(), TimelineEvent.id.desc()).limit(
        filters.limit + 1
    ).all()
    has_more = len(rows) > filters.limit
    page = rows[: filters.limit]
    next_cursor = _encode_cursor(page[-1][0], filters) if has_more and page else None
    return {
        "events": [_serialize_monitor_event(row, role=role) for row in page],
        "page": {
            "count": len(page),
            "limit": filters.limit,
            "has_more": has_more,
            "next_cursor": next_cursor,
        },
        "filters": filters.model_dump(mode="json", exclude={"cursor"}, exclude_none=True),
    }


def get_monitor_event(
    db: Session,
    *,
    patient_id: int,
    event_id: str,
    role: str,
    viewer_id: int,
):
    query = _joined_query(db).filter(TimelineEvent.patient_id == patient_id)
    query = _apply_viewer_scope(query, role=role, viewer_id=viewer_id)
    row = query.filter(TimelineEvent.event_id == event_id).first()
    if row is None:
        raise LookupError("Monitor event not found")
    return _serialize_monitor_event(row, include_payload=True, role=role)


def monitor_summary(db: Session, *, filters: EventMonitorFilters, role: str, viewer_id: int):
    rows = _apply_viewer_scope(
        _apply_filters(_joined_query(db), filters),
        role=role,
        viewer_id=viewer_id,
    ).yield_per(500)
    statuses = Counter()
    event_types = Counter()
    integrity = Counter()
    latencies = []
    anomaly_count = 0
    latest_event_at = None
    stale_before = datetime.now(timezone.utc) - timedelta(minutes=5)
    stale_unacknowledged = 0
    total = 0

    for row in rows:
        total += 1
        event, outbound, acknowledgement, received = row
        status_value = _delivery_status(outbound, acknowledgement)
        integrity_status, _ = _payload_integrity(event)
        statuses[status_value] += 1
        event_types[event.event_type] += 1
        integrity[integrity_status] += 1
        anomaly_count += len(_anomalies(event, outbound, acknowledgement, received, integrity_status))
        latency = _delivery_latency_ms(event, acknowledgement)
        if latency is not None:
            latencies.append(latency)
        occurred = event.occurred_at
        if occurred and (latest_event_at is None or occurred > latest_event_at):
            latest_event_at = occurred
        if outbound is not None and status_value in {"pending", "sent", "failed"}:
            created = outbound.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created and created < stale_before:
                stale_unacknowledged += 1

    acknowledged = statuses["acknowledged"]
    return {
        "patient_id": filters.patient_id,
        "total_events": total,
        "delivery_counts": {
            key: statuses[key]
            for key in ("pending", "sent", "acknowledged", "failed", "untracked")
        },
        "event_type_counts": dict(sorted(event_types.items())),
        "acknowledgement_rate": round((acknowledged / total) * 100, 2) if total else 0.0,
        "average_delivery_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "latest_event_at": latest_event_at,
        "integrity_counts": {
            key: integrity[key] for key in ("verified", "legacy_unverified", "mismatch")
        },
        "anomaly_count": anomaly_count,
        "stale_unacknowledged": stale_unacknowledged,
        "health": (
            "attention"
            if statuses["failed"] or statuses["untracked"] or integrity["mismatch"] or stale_unacknowledged
            else "healthy"
        ),
        "filters": filters.model_dump(mode="json", exclude_none=True),
    }
