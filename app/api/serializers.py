from fastapi import Request

from app.models.consent import ConsentAcceptance
from app.models.session import UserSession
from app.models.user import User


def client_ip(request: Request):
    return request.client.host if request.client else None


def serialize_user(user: User):
    return {
        "id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "mobile_number": user.mobile_number,
    }


def serialize_session(session: UserSession):
    return {
        "session_token": session.session_token,
        "expires_at": session.expires_at,
        "is_active": session.is_active,
    }


def serialize_consent(consent: ConsentAcceptance):
    return {
        "patient_id": consent.patient_id,
        "consent_version": consent.consent_version,
        "accepted_at": consent.accepted_at,
        "application_name": consent.application_name,
        "app_version": consent.app_version,
        "ip_address": consent.ip_address,
    }


def serialize_auth_result(result):
    response = {
        "user": serialize_user(result["user"]),
        "session": serialize_session(result["session"]),
        "dashboard_route": result["dashboard_route"],
    }
    if "consent" in result:
        response["consent"] = serialize_consent(result["consent"])
    return response
