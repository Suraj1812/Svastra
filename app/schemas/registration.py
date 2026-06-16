import json
from datetime import date
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.config import settings


@lru_cache(maxsize=1)
def _reference_terms() -> Dict[str, List[str]]:
    if not settings.reference_terms_path.exists():
        return {}

    with settings.reference_terms_path.open(encoding="utf-8") as terms_file:
        data = json.load(terms_file)

    if isinstance(data, dict):
        return {tag: [str(value) for value in values] for tag, values in data.items()}

    terms = {}
    for item in data:
        tag = item.get("tag")
        value = item.get("term") or item.get("value")
        if tag and value:
            terms.setdefault(tag, []).append(str(value))

    return terms


def _validate_reference_value(tag: str, value: str):
    allowed_values = _reference_terms().get(tag, [])
    if allowed_values and value not in allowed_values:
        raise ValueError(f"Allowed {tag} values: {', '.join(allowed_values)}")
    return value


def _validate_mobile_number(value: str):
    digit_count = sum(1 for character in value if character.isdigit())
    if digit_count < 10 or digit_count > 15:
        raise ValueError("Mobile number must contain 10 to 15 digits")
    return value


class RegistrationBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=1)
    mobile_number: str = Field(..., min_length=10, max_length=20)
    terms_accepted: bool

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value):
        return _validate_mobile_number(value)

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms_accepted(cls, value):
        if value is not True:
            raise ValueError("Terms acceptance is required")
        return value


class ProviderRegistration(RegistrationBase):
    email_address: Optional[EmailStr] = None
    professional_category: str = Field(..., min_length=1)
    registration_number: str = Field(..., min_length=1)
    hpid_number: Optional[str] = None

    @field_validator("professional_category")
    @classmethod
    def validate_professional_category(cls, value):
        return _validate_reference_value("occupation", value)


class PatientRegistration(RegistrationBase):
    date_of_birth: date
    gender: str = Field(..., min_length=1)
    preferred_language: str = Field(..., min_length=1)
    abha_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_mobile: Optional[str] = None
    unified_consent_accepted: bool

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value):
        return _validate_reference_value("gender", value)

    @field_validator("preferred_language")
    @classmethod
    def validate_preferred_language(cls, value):
        return _validate_reference_value("language", value)

    @field_validator("emergency_contact_mobile")
    @classmethod
    def validate_emergency_contact_mobile(cls, value):
        if value is None:
            return value
        return _validate_mobile_number(value)

    @field_validator("unified_consent_accepted")
    @classmethod
    def validate_unified_consent_accepted(cls, value):
        if value is not True:
            raise ValueError("Unified consent acceptance is required")
        return value


class CaregiverRegistration(RegistrationBase):
    relationship_to_patient: str = Field(..., min_length=1)
    preferred_language: str = Field(..., min_length=1)

    @field_validator("relationship_to_patient")
    @classmethod
    def validate_relationship_to_patient(cls, value):
        return _validate_reference_value("relationship", value)

    @field_validator("preferred_language")
    @classmethod
    def validate_preferred_language(cls, value):
        return _validate_reference_value("language", value)
