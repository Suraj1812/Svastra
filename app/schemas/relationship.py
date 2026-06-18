from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int = Field(..., gt=0)
    confirmed: Literal[True]
