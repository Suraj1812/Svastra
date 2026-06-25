from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class DiagnosisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    conceptId: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )
    term: str = Field(..., min_length=2, max_length=160)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("conceptId", mode="before")
    @classmethod
    def blank_concept_id_is_optional(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class CarePlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=3, max_length=160)
    diagnosis: Optional[Union[DiagnosisRequest, str]] = None

    @field_validator("diagnosis")
    @classmethod
    def legacy_diagnosis_length(cls, value):
        if isinstance(value, str) and len(value) > 255:
            raise ValueError("Diagnosis must be 255 characters or fewer")
        return value


class CarePlanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=3, max_length=160)
    diagnosis: Optional[Union[DiagnosisRequest, str]] = None

    @field_validator("diagnosis")
    @classmethod
    def legacy_diagnosis_length(cls, value):
        if isinstance(value, str) and len(value) > 255:
            raise ValueError("Diagnosis must be 255 characters or fewer")
        return value


class ValueWarning(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    condition: Literal["more_than", "less_than", "at_least", "at_most", "equal_to"]
    threshold_value: float = Field(..., ge=-1000000, le=1000000)
    measurement_unit: str = Field(..., min_length=1, max_length=24)
    notification: Notification = "immediate"
    severity: Literal["low", "medium", "high", "critical"] = "high"


class NonResponseWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinical_grace_minutes: int = Field(..., ge=1, le=1440)
    notification: Notification = "immediate"
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class BaseConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: Frequency
    additional_instructions: Optional[str] = Field(default=None, max_length=500)
    duration_value: int = Field(..., ge=1, le=365)
    duration_unit: DurationUnit
    non_response_warning: Optional[NonResponseWarning] = None


class MedicationConfiguration(BaseConfiguration):
    dose_value: float = Field(..., gt=0, le=1000000)
    dose_unit: Literal["mcg", "mg", "g", "mL", "tablet", "capsule", "drop", "puff", "unit"]
    route: Literal["oral", "topical", "inhaled", "injection", "other"]


class MeasurementConfiguration(BaseConfiguration):
    measurement_unit: str = Field(..., min_length=1, max_length=24)
    value_warning: Optional[ValueWarning] = None

    @model_validator(mode="after")
    def warning_unit_must_match(self):
        if self.value_warning and self.value_warning.measurement_unit != self.measurement_unit:
            raise ValueError("Value-warning unit must match the measurement unit")
        return self


class InvestigationConfiguration(BaseConfiguration):
    priority: Literal["routine", "urgent", "asap", "stat"]
    due_date: date
    upload_required: Literal[True] = True
    alert_if_not_uploaded: bool = True
    grace_period_value: int = Field(default=2, ge=0, le=30)
    grace_period_unit: Literal["hours", "days"] = "days"

    @field_validator("due_date")
    @classmethod
    def due_date_is_reasonable(cls, value: date):
        today = date.today()
        if value < today:
            raise ValueError("Investigation due date cannot be in the past")
        if value > today + timedelta(days=366 * 5):
            raise ValueError("Investigation due date cannot be more than five years ahead")
        return value


class RecommendationConfiguration(BaseConfiguration):
    pass


class AllergyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    allergen_term: str = Field(..., min_length=2, max_length=160)


class AdvisoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )
    term: str = Field(..., min_length=1, max_length=255)
    tag: Literal["medication", "measurement", "recommendation", "investigation"]
    configuration: dict


class PublishCarePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]
