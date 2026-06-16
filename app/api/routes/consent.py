from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip, serialize_consent
from app.audit.audit_service import record_audit_event
from app.consent.consent_service import (
    get_current_consent_document,
    get_current_consent_version,
    get_pending_consent_requests,
    get_patient_consent_status,
    grant_consent_request,
    record_consent_acceptance,
    reject_consent_request,
)
from app.core.responses import success_response
from app.database import get_db
from app.schemas.consent import ConsentAcceptanceRequest, ConsentDecisionRequest


router = APIRouter(prefix="/consent", tags=["Consent"])


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
    requests = get_pending_consent_requests(db, patient_id=current_user.id)
    return success_response({"requests": requests})


@router.post("/request/{request_id}/grant")
def grant_request(
    request_id: str,
    payload: ConsentDecisionRequest,
    current_user=Depends(get_current_user),
):
    try:
        result = grant_consent_request(request_id=request_id, otp=payload.otp, actor_user=current_user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return success_response(result, "Consent request grant placeholder completed")


@router.post("/request/{request_id}/reject")
def reject_request(
    request_id: str,
    payload: ConsentDecisionRequest,
    current_user=Depends(get_current_user),
):
    try:
        result = reject_consent_request(request_id=request_id, otp=payload.otp, actor_user=current_user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return success_response(result, "Consent request reject placeholder completed")


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
