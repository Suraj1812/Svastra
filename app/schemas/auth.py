from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_mobile_number(value: str):
    digit_count = sum(1 for character in value if character.isdigit())
    if digit_count < 10 or digit_count > 15:
        raise ValueError("Mobile number must contain 10 to 15 digits")
    return value


class MobileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mobile_number: str = Field(..., min_length=10, max_length=20)

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value):
        return _validate_mobile_number(value)


class OTPVerifyRequest(MobileRequest):
    otp: str = Field(..., min_length=4, max_length=8)


class SessionTokenRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    session_token: str = Field(..., min_length=1)
