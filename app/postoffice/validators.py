from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SUPPORTED_EVENT_TYPES = (
    "consent.request",
    "consent.grant",
    "consent.reject",
    "consent.revoke",
    "relationship.created",
    "relationship.deactivated",
    "advisory.publish",
    "response.log",
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
        "advisory.publish",
        "response.log",
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
        elif self.event_type.startswith("relationship."):
            _non_empty(self.payload, "relationship_id")
            _positive_int(self.payload, "linked_user_id")
            _non_empty(self.payload, "relationship_type")
            _non_empty(self.payload, "status")
        elif self.event_type == "advisory.publish":
            _positive_int(self.payload, "care_plan_id")
            advisories = self.payload.get("advisories")
            if not isinstance(advisories, list) or not advisories:
                raise ValueError("payload.advisories must be a non-empty list")
        elif self.event_type == "response.log":
            _non_empty(self.payload, "task_id")
            _non_empty(self.payload, "response_type")
        elif self.event_type == "alert.trigger":
            _non_empty(self.payload, "alert_id")
            _non_empty(self.payload, "severity")
        elif self.event_type == "message.send":
            _non_empty(self.payload, "message_id")
            _non_empty(self.payload, "message_text")
        return self


class AcknowledgementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(..., min_length=8, max_length=64)
    received_by: str = Field(..., min_length=2, max_length=64)
    status: Literal["received"] = "received"


def _positive_int(payload: dict[str, Any], field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"payload.{field_name} must be a positive integer")


def _non_empty(payload: dict[str, Any], field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{field_name} must be a non-empty string")


def validate_event(event: CEPEvent | dict):
    try:
        return event if isinstance(event, CEPEvent) else CEPEvent.model_validate(event)
    except Exception as error:
        raise CEPValidationError(str(error)) from error
