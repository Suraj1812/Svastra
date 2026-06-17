from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip, serialize_consent, serialize_relationship_consent
from app.audit.audit_service import record_audit_event
from app.consent.consent_service import (
    create_consent_request,
    get_active_consents,
    get_current_consent_document,
    get_current_consent_version,
    get_inactive_consents,
    get_pending_consents,
    get_pending_consent_requests,
    get_patient_consent_status,
    get_relationship_consent,
    grant_consent,
    record_consent_acceptance,
    reject_consent,
    revoke_consent,
    send_consent_otp,
    update_consent_alias,
    verify_consent_otp,
)
from app.core.responses import success_response
from app.database import get_db
from app.rbac.permission_validator import authorize_request
from app.schemas.consent import (
    ConsentAcceptanceRequest,
    ConsentAliasUpdateRequest,
    ConsentDecisionRequest,
    ConsentOTPRequest,
    ConsentOTPVerifyRequest,
    RelationshipConsentRequest,
)


router = APIRouter(prefix="/consent", tags=["Consent"])


def _relationship_error(error: Exception):
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _require_patient_consent_admin(current_user):
    authorize_request(current_user, "MANAGE_CONSENT")


def _request_permission_for(consent_type: str):
    if consent_type == "provider_access":
        return "REQUEST_PATIENT_ACCESS"
    if consent_type == "caregiver_access":
        return "REQUEST_CAREGIVER_ACCESS"
    return "MANAGE_CONSENT"


@router.get("/current")
def current_consent(db: Session = Depends(get_db)):
    return success_response(
        {
            "consent_version": get_current_consent_version(db),
            "document": get_current_consent_document(),
        }
    )


@router.post("/platform/accept", status_code=status.HTTP_201_CREATED)
def accept_platform_consent(
    payload: ConsentAcceptanceRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform consent can only be accepted by patients",
        )

    consent = record_consent_acceptance(
        db,
        patient_id=current_user.id,
        application_name=payload.application_name,
        app_version=payload.app_version,
        ip_address=client_ip(request),
    )
    record_audit_event(
        db,
        action="consent.platform.accept",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        mobile_number=current_user.mobile_number,
        ip_address=client_ip(request),
        success=True,
        metadata={"consent_version": consent.consent_version},
    )
    return success_response(serialize_consent(consent), "Platform consent recorded")


@router.get("/requests")
def pending_consent_requests(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_patient_consent_admin(current_user)
    requests = get_pending_consent_requests(db, patient_id=current_user.id)
    return success_response(
        {"requests": [serialize_relationship_consent(consent) for consent in requests]}
    )


@router.get("/active")
def active_consents(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_patient_consent_admin(current_user)
    consents = get_active_consents(db, patient_id=current_user.id)
    return success_response(
        {"consents": [serialize_relationship_consent(consent) for consent in consents]}
    )


@router.get("/pending")
def pending_consents(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_patient_consent_admin(current_user)
    consents = get_pending_consents(db, patient_id=current_user.id)
    return success_response(
        {"requests": [serialize_relationship_consent(consent) for consent in consents]}
    )


@router.get("/inactive")
def inactive_consents(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_patient_consent_admin(current_user)
    consents = get_inactive_consents(db, patient_id=current_user.id)
    return success_response(
        {"consents": [serialize_relationship_consent(consent) for consent in consents]}
    )


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_relationship_consent(
    payload: RelationshipConsentRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorize_request(current_user, _request_permission_for(payload.consent_type))
    try:
        consent = create_consent_request(
            db,
            patient_id=payload.patient_id,
            requestor_user=current_user,
            consent_type=payload.consent_type,
            alias=payload.alias,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(
        serialize_relationship_consent(consent),
        "Consent request created",
    )


@router.post("/send-otp")
def send_relationship_consent_otp(
    payload: ConsentOTPRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = get_relationship_consent(db, consent_id=payload.consent_id)
        if consent.patient_id != current_user.id:
            raise PermissionError("Patient authority is required for this consent")
        result = send_consent_otp(current_user)
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(
        {
            "consent_id": payload.consent_id,
            "action": payload.action,
            "otp_sent": result["success"],
            "mobile_number": current_user.mobile_number,
        },
        "Consent OTP sent",
    )


@router.post("/verify-otp")
def verify_relationship_consent_otp(
    payload: ConsentOTPVerifyRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = get_relationship_consent(db, consent_id=payload.consent_id)
        if consent.patient_id != current_user.id:
            raise PermissionError("Patient authority is required for this consent")
        verify_consent_otp(current_user, payload.otp)
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(
        {
            "consent_id": payload.consent_id,
            "action": payload.action,
            "otp_verified": True,
        },
        "Consent OTP verified",
    )


@router.post("/request/{request_id}/grant")
def grant_request(
    request_id: str,
    payload: ConsentDecisionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = grant_consent(
            db,
            consent_id=int(request_id),
            otp=payload.otp,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(serialize_relationship_consent(consent), "Consent granted")


@router.post("/request/{request_id}/reject")
def reject_request(
    request_id: str,
    payload: ConsentDecisionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = reject_consent(
            db,
            consent_id=int(request_id),
            otp=payload.otp,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(serialize_relationship_consent(consent), "Consent rejected")


@router.post("/request/{request_id}/revoke")
def revoke_request(
    request_id: str,
    payload: ConsentDecisionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = revoke_consent(
            db,
            consent_id=int(request_id),
            otp=payload.otp,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(serialize_relationship_consent(consent), "Consent revoked")


@router.put("/{consent_id}/alias")
def update_relationship_consent_alias(
    consent_id: int,
    payload: ConsentAliasUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = update_consent_alias(
            db,
            consent_id=consent_id,
            actor_user=current_user,
            alias=payload.alias,
        )
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(serialize_relationship_consent(consent), "Consent alias updated")


@router.get("/{consent_id}")
def relationship_consent_detail(
    consent_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_patient_consent_admin(current_user)
    try:
        consent = get_relationship_consent(db, consent_id=consent_id)
        if consent.patient_id != current_user.id:
            raise PermissionError("Patient authority is required for this consent")
    except (ValueError, PermissionError) as error:
        _relationship_error(error)
    return success_response(serialize_relationship_consent(consent, include_mobile=True))


@router.post("/patients/{patient_id}/accept", status_code=status.HTTP_201_CREATED)
def accept_consent(
    patient_id: int,
    payload: ConsentAcceptanceRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        consent = record_consent_acceptance(
            db,
            patient_id=patient_id,
            application_name=payload.application_name,
            app_version=payload.app_version,
            ip_address=client_ip(request),
        )
    except ValueError as error:
        record_audit_event(
            db,
            action="consent.accept",
            actor_user_id=patient_id,
            actor_role="patient",
            ip_address=client_ip(request),
            success=False,
            metadata={"reason": str(error)},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    record_audit_event(
        db,
        action="consent.accept",
        actor_user_id=patient_id,
        actor_role="patient",
        ip_address=client_ip(request),
        success=True,
        metadata={"consent_version": consent.consent_version},
    )
    return success_response(serialize_consent(consent), "Consent recorded")


@router.get("/patients/{patient_id}/status")
def patient_consent_status(patient_id: int, db: Session = Depends(get_db)):
    return success_response(get_patient_consent_status(db, patient_id))
