from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.reference_terms import validate_reference_term


class ReferenceTerm(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    conceptId: str = Field(..., min_length=1)
    term: str = Field(..., min_length=1)
    tag: str = Field(..., min_length=1)


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
    professional_category: ReferenceTerm
    registration_number: str = Field(..., min_length=1)
    hpid_number: Optional[str] = None

    @field_validator("professional_category")
    @classmethod
    def validate_professional_category(cls, value):
        return ReferenceTerm(**validate_reference_term("occupation", value))


class PatientRegistration(RegistrationBase):
    date_of_birth: date
    gender: ReferenceTerm
    preferred_language: ReferenceTerm
    abha_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_mobile: Optional[str] = None
    unified_consent_accepted: bool

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value):
        return ReferenceTerm(**validate_reference_term("gender", value))

    @field_validator("preferred_language")
    @classmethod
    def validate_preferred_language(cls, value):
        return ReferenceTerm(**validate_reference_term("language", value))

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
    relationship_to_patient: ReferenceTerm
    preferred_language: ReferenceTerm

    @field_validator("relationship_to_patient")
    @classmethod
    def validate_relationship_to_patient(cls, value):
        return ReferenceTerm(**validate_reference_term("relationship", value))

    @field_validator("preferred_language")
    @classmethod
    def validate_preferred_language(cls, value):
        return ReferenceTerm(**validate_reference_term("language", value))
