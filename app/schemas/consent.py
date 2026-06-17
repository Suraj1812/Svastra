from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConsentAcceptanceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    application_name: Optional[str] = None
    app_version: Optional[str] = None


class ConsentDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    otp: str = Field(..., min_length=4, max_length=8)


class RelationshipConsentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    patient_id: int
    consent_type: Literal["provider_access", "caregiver_access"]
    alias: Optional[str] = Field(default=None, max_length=60)


class ConsentOTPRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    consent_id: int
    action: Literal["grant", "reject", "revoke"]


class ConsentOTPVerifyRequest(ConsentOTPRequest):
    otp: str = Field(..., min_length=4, max_length=8)


class ConsentAliasUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    alias: str = Field(..., min_length=1, max_length=60)
