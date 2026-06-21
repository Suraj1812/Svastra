from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


TaskExecutionStatus = Literal["pending", "completed", "completed_late", "missed"]
TaskResponseStatus = Literal["taken", "missed", "done", "recorded"]


class CodedReason(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    concept_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )
    term: str = Field(..., min_length=1, max_length=160)


class TaskResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    response_status: TaskResponseStatus
    reason: Optional[CodedReason] = None
    numeric_value: Optional[float] = Field(default=None, ge=-1000000, le=1000000)
    measurement_unit: Optional[str] = Field(default=None, min_length=1, max_length=24)

    @model_validator(mode="after")
    def reason_is_only_for_missed(self):
        if self.response_status != "missed" and self.reason is not None:
            raise ValueError("A coded reason is accepted only for a missed response")
        if (self.numeric_value is None) != (self.measurement_unit is None):
            raise ValueError("numeric_value and measurement_unit must be supplied together")
        return self


class AlertAcknowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]


class EvaluateOverdueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: Optional[int] = Field(default=None, gt=0)
