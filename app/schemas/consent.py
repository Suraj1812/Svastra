from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConsentAcceptanceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_name: Optional[str] = None
    app_version: Optional[str] = None


class ConsentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]


class RelationshipConsentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    patient_id: int = Field(..., gt=0)
    consent_type: Literal["provider_access", "caregiver_access"]
    alias: Optional[str] = Field(default=None, max_length=60)


class ConsentAliasUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    alias: str = Field(..., min_length=1, max_length=60)
