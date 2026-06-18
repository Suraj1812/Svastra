from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


Frequency = Literal[
    "once_daily",
    "twice_daily",
    "three_times_daily",
    "four_times_daily",
    "every_4_hours",
    "every_6_hours",
    "weekly",
    "monthly",
    "as_needed",
]
DurationUnit = Literal["hours", "days", "weeks", "months"]
Notification = Literal["immediate", "daily_summary", "both", "none"]


class CarePlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=3, max_length=160)
    diagnosis: Optional[str] = Field(default=None, max_length=255)


class ValueWarning(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    condition: Literal["more_than", "less_than", "at_least", "at_most", "equal_to"]
    threshold_value: float
    measurement_unit: str = Field(..., min_length=1, max_length=24)
    notification: Notification = "immediate"


class NonResponseWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinical_grace_minutes: int = Field(..., ge=1, le=1440)
    notification: Notification


class BaseConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: Frequency
    additional_instructions: Optional[str] = Field(default=None, max_length=500)
    duration_value: int = Field(..., ge=1, le=365)
    duration_unit: DurationUnit
    non_response_warning: Optional[NonResponseWarning] = None


class MedicationConfiguration(BaseConfiguration):
    dose: str = Field(..., min_length=1, max_length=80)


class MeasurementConfiguration(BaseConfiguration):
    measurement_unit: str = Field(..., min_length=1, max_length=24)
    value_warning: Optional[ValueWarning] = None

    @model_validator(mode="after")
    def warning_unit_must_match(self):
        if self.value_warning and self.value_warning.measurement_unit != self.measurement_unit:
            raise ValueError("Value-warning unit must match the measurement unit")
        return self


class InvestigationConfiguration(BaseConfiguration):
    priority: Literal["routine", "urgent", "stat"]
    attachment_required: bool = True


class RecommendationConfiguration(BaseConfiguration):
    pass


class AdvisoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    concept_id: str = Field(..., min_length=1, max_length=64)
    term: str = Field(..., min_length=1, max_length=255)
    tag: Literal["medication", "measurement", "recommendation", "investigation"]
    configuration: dict


class PublishCarePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]
