from fastapi import Request

from app.models.consent import ConsentAcceptance, RelationshipConsent
from app.models.session import UserSession
from app.models.user import User
from app.reference_terms import decode_reference_term


def client_ip(request: Request):
    return request.client.host if request.client else None


def serialize_user(user: User):
    return {
        "id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "mobile_number": user.mobile_number,
        "professional_category": decode_reference_term(user.professional_category, "occupation"),
        "gender": decode_reference_term(user.gender, "gender"),
        "preferred_language": decode_reference_term(user.preferred_language, "language"),
        "relationship_to_patient": decode_reference_term(
            user.relationship_to_patient,
            "relationship",
        ),
    }


def serialize_session(session: UserSession):
    data = {
        "expires_at": session.expires_at,
        "is_active": session.is_active,
    }
    if session.session_token is not None:
        data["session_token"] = session.session_token
    return data


def serialize_consent(consent: ConsentAcceptance):
    return {
        "patient_id": consent.patient_id,
        "consent_version": consent.consent_version,
        "accepted_at": consent.accepted_at,
        "application_name": consent.application_name,
        "app_version": consent.app_version,
        "ip_address": consent.ip_address,
    }


def serialize_relationship_consent(consent: RelationshipConsent, include_mobile: bool = False):
    requestor = consent.requestor
    data = {
        "id": consent.id,
        "alias": consent.alias,
        "registered_full_name": requestor.full_name,
        "requestor_name": requestor.full_name,
        "requestor_role": consent.requestor_role,
        "role": consent.requestor_role,
        "consent_type": consent.consent_type,
        "status": consent.status,
        "request_date": consent.requested_at,
        "granted_date": consent.granted_at,
        "decision_date": consent.revoked_at or consent.rejected_at or consent.expired_at or consent.granted_at,
        "revoked_date": consent.revoked_at,
        "rejected_date": consent.rejected_at,
        "expired_date": consent.expired_at,
        "relevant_dates": {
            "requested_at": consent.requested_at,
            "granted_at": consent.granted_at,
            "rejected_at": consent.rejected_at,
            "revoked_at": consent.revoked_at,
            "expired_at": consent.expired_at,
        },
    }
    if include_mobile:
        data["mobile_number"] = requestor.mobile_number
    return data


def serialize_auth_result(result):
    response = {
        "user": serialize_user(result["user"]),
        "session": serialize_session(result["session"]),
        "dashboard_route": result["dashboard_route"],
    }
    if "consent" in result:
        response["consent"] = serialize_consent(result["consent"])
    return response
