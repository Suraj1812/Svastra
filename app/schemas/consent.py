from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConsentAcceptanceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    application_name: Optional[str] = None
    app_version: Optional[str] = None


class ConsentDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    otp: str = Field(..., min_length=4, max_length=8)
