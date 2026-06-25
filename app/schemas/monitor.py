from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import settings


MonitorDeliveryStatus = Literal["pending", "sent", "acknowledged", "failed", "untracked"]
MonitorEventType = Literal[
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
    "alert.acknowledge",
    "alert.resolve",
    "message.send",
]


class EventMonitorFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: int = Field(..., gt=0)
    event_type: Optional[MonitorEventType] = None
    delivery_status: Optional[MonitorDeliveryStatus] = None
    source: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$",
    )
    target: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$",
    )
    event_id_prefix: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    )
    occurred_from: Optional[datetime] = None
    occurred_to: Optional[datetime] = None

    @field_validator("occurred_from", "occurred_to")
    @classmethod
    def timestamps_require_timezone(cls, value: datetime | None):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("monitor timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_time_window(self):
        if self.occurred_from and self.occurred_to:
            if self.occurred_from > self.occurred_to:
                raise ValueError("occurred_from must be earlier than occurred_to")
            if (self.occurred_to - self.occurred_from).days > settings.monitor_max_window_days:
                raise ValueError(
                    f"monitor time window cannot exceed {settings.monitor_max_window_days} days"
                )
        return self


class EventMonitorQuery(EventMonitorFilters):
    limit: int = Field(default=25, ge=1, le=settings.monitor_max_page_size)
    cursor: Optional[str] = Field(default=None, min_length=20, max_length=512)


class EventMonitorSummaryQuery(EventMonitorFilters):
    pass
