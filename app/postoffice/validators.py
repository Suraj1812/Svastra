from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SUPPORTED_EVENT_TYPES = (
    "consent.request",
    "consent.grant",
    "consent.reject",
    "consent.revoke",
    "relationship.created",
    "relationship.deactivated",
    "schedule.generate",
    "advisory.publish",
    "task.generate",
    "response.log",
    "attachment.upload",
    "alert.trigger",
    "message.send",
)

_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")
_MAX_PAYLOAD_BYTES = 64 * 1024


class CEPValidationError(ValueError):
    pass


class CEPEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: Literal[
        "consent.request",
        "consent.grant",
        "consent.reject",
        "consent.revoke",
        "relationship.created",
        "relationship.deactivated",
        "schedule.generate",
        "advisory.publish",
        "task.generate",
        "response.log",
        "attachment.upload",
        "alert.trigger",
        "message.send",
    ]
    event_id: str = Field(..., min_length=8, max_length=64)
    timestamp: datetime
    source: str = Field(..., min_length=2, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    payload: dict[str, Any]

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str):
        if not _EVENT_ID_PATTERN.fullmatch(value):
            raise ValueError("event_id may contain only letters, numbers, dot, underscore, colon, or hyphen")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        if value.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("timestamp cannot be more than five minutes in the future")
        return value

    @model_validator(mode="after")
    def validate_payload_shape(self):
        if len(json.dumps(self.payload, default=str).encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError("payload exceeds the 64 KiB limit")

        _positive_int(self.payload, "patient_id")
        _positive_int(self.payload, "actor_id")

        if self.event_type.startswith("consent."):
            _positive_int(self.payload, "consent_id")
            _positive_int(self.payload, "requestor_id")
            _non_empty(self.payload, "status")
            expected_status = {
                "consent.request": "PENDING",
                "consent.grant": "ACTIVE",
                "consent.reject": "REJECTED",
                "consent.revoke": "REVOKED",
            }[self.event_type]
            if self.payload["status"] != expected_status:
                raise ValueError(f"payload.status must be {expected_status} for {self.event_type}")
            _one_of(self.payload, "requestor_role", {"provider", "caregiver"})
            _one_of(self.payload, "consent_type", {"provider_access", "caregiver_access"})
        elif self.event_type.startswith("relationship."):
            _non_empty(self.payload, "relationship_id")
            _positive_int(self.payload, "linked_user_id")
            _non_empty(self.payload, "relationship_type")
            _non_empty(self.payload, "status")
            _one_of(
                self.payload,
                "relationship_type",
                {"provider_patient", "patient_caregiver"},
            )
            expected_status = "ACTIVE" if self.event_type == "relationship.created" else "INACTIVE"
            if self.payload["status"] != expected_status:
                raise ValueError(f"payload.status must be {expected_status} for {self.event_type}")
        elif self.event_type in {"schedule.generate", "task.generate"}:
            _positive_int(self.payload, "care_plan_id")
            _positive_int(self.payload, "advisory_id")
            if self.event_type == "schedule.generate":
                _positive_int(self.payload, "task_count")
            else:
                task_ids = self.payload.get("task_ids")
                if not isinstance(task_ids, list) or not task_ids or len(task_ids) > 500:
                    raise ValueError("payload.task_ids must contain 1 to 500 task identifiers")
                if len(set(task_ids)) != len(task_ids):
                    raise ValueError("payload.task_ids cannot contain duplicates")
                for index, task_id in enumerate(task_ids):
                    if not isinstance(task_id, str) or not 8 <= len(task_id) <= 64:
                        raise ValueError(f"payload.task_ids.{index} must be 8 to 64 characters")
        elif self.event_type == "advisory.publish":
            _positive_int(self.payload, "care_plan_id")
            _one_of(self.payload, "execution_status", {"pending"})
            advisories = self.payload.get("advisories")
            if not isinstance(advisories, list) or not advisories:
                raise ValueError("payload.advisories must be a non-empty list")
            if len(advisories) > 50:
                raise ValueError("payload.advisories cannot contain more than 50 items")
            for index, advisory in enumerate(advisories):
                if not isinstance(advisory, dict):
                    raise ValueError(f"payload.advisories.{index} must be an object")
                _positive_int(advisory, "advisory_id", prefix=f"payload.advisories.{index}")
                _bounded_string(advisory, "concept_id", 1, 64, prefix=f"payload.advisories.{index}")
                _one_of(
                    advisory,
                    "advisory_type",
                    {"medication", "measurement", "recommendation", "investigation"},
                    prefix=f"payload.advisories.{index}",
                )
                _one_of(
                    advisory,
                    "tag",
                    {"medication", "measurement", "recommendation", "investigation"},
                    prefix=f"payload.advisories.{index}",
                )
                if advisory["tag"] != advisory["advisory_type"]:
                    raise ValueError(
                        f"payload.advisories.{index}.tag must match advisory_type"
                    )
                _bounded_string(advisory, "term", 1, 255, prefix=f"payload.advisories.{index}")
                _one_of(
                    advisory,
                    "execution_status",
                    {"pending"},
                    prefix=f"payload.advisories.{index}",
                )
                if not isinstance(advisory.get("configuration"), dict):
                    raise ValueError(f"payload.advisories.{index}.configuration must be an object")
        elif self.event_type == "response.log":
            _bounded_string(self.payload, "task_id", 1, 100)
            _one_of(
                self.payload,
                "response_type",
                {"medication", "measurement", "recommendation", "investigation"},
            )
            _one_of(
                self.payload,
                "response_status",
                {"taken", "missed", "done", "recorded", "uploaded"},
            )
            _one_of(
                self.payload,
                "execution_status",
                {"completed", "completed_late", "missed"},
            )
        elif self.event_type == "attachment.upload":
            _bounded_string(self.payload, "task_id", 1, 100)
            _bounded_string(self.payload, "attachment_id", 1, 100)
            _bounded_string(self.payload, "filename", 1, 180)
            _bounded_string(self.payload, "content_type", 3, 64)
            _bounded_string(self.payload, "sha256", 64, 64)
            _one_of(self.payload, "response_type", {"investigation"})
            _one_of(self.payload, "execution_status", {"completed", "completed_late"})
        elif self.event_type == "alert.trigger":
            _bounded_string(self.payload, "alert_id", 1, 100)
            _one_of(self.payload, "severity", {"low", "medium", "high", "critical"})
        elif self.event_type == "message.send":
            _bounded_string(self.payload, "message_id", 1, 100)
            _bounded_string(self.payload, "message_text", 1, 4000)
        return self


class AcknowledgementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(..., min_length=8, max_length=64)
    received_by: str = Field(..., min_length=2, max_length=64)
    status: Literal["received"] = "received"

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str):
        if not _EVENT_ID_PATTERN.fullmatch(value):
            raise ValueError("event_id format is invalid")
        return value


def _positive_int(payload: dict[str, Any], field_name: str, prefix: str = "payload"):
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{prefix}.{field_name} must be a positive integer")


def _non_empty(payload: dict[str, Any], field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{field_name} must be a non-empty string")


def _bounded_string(
    payload: dict[str, Any],
    field_name: str,
    minimum: int,
    maximum: int,
    prefix: str = "payload",
):
    value = payload.get(field_name)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{prefix}.{field_name} must contain {minimum} to {maximum} characters")


def _one_of(
    payload: dict[str, Any],
    field_name: str,
    allowed: set[str],
    prefix: str = "payload",
):
    value = payload.get(field_name)
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{prefix}.{field_name} must be one of: {choices}")


def validate_event(event: CEPEvent | dict):
    try:
        return event if isinstance(event, CEPEvent) else CEPEvent.model_validate(event)
    except Exception as error:
        raise CEPValidationError(str(error)) from error
