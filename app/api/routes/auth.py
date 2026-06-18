from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.serializers import (
    client_ip,
    serialize_auth_result,
    serialize_session,
    serialize_user,
)
from app.audit.audit_service import record_audit_event
from app.auth import auth_service, otp_provider
from app.auth.session_manager import logout, validate_session
from app.core.responses import success_response
from app.database import get_db
from app.schemas.auth import MobileRequest, OTPVerifyRequest, SessionTokenRequest
from app.schemas.registration import (
    CaregiverRegistration,
    PatientRegistration,
    ProviderRegistration,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/otp/send")
def send_otp(payload: MobileRequest, request: Request, db: Session = Depends(get_db)):
    result = otp_provider.send_otp(payload.mobile_number)
    record_audit_event(
        db,
        action="otp.send",
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=result["success"],
    )
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"OTP was recently sent; retry in {result['retry_after_seconds']} seconds",
        )
    return success_response(result, "OTP sent successfully")


@router.post("/otp/verify")
def verify_otp(payload: OTPVerifyRequest, request: Request, db: Session = Depends(get_db)):
    if not otp_provider.verify_otp(payload.mobile_number, payload.otp):
        record_audit_event(
            db,
            action="otp.verify",
            mobile_number=payload.mobile_number,
            ip_address=client_ip(request),
            success=False,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    record_audit_event(
        db,
        action="otp.verify",
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=True,
    )
    return success_response(
        {"mobile_number": payload.mobile_number, "otp_verified": True},
        "OTP verified successfully",
    )


@router.post("/register/provider", status_code=status.HTTP_201_CREATED)
def register_provider(
    payload: ProviderRegistration,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = auth_service.register_provider(db, payload)
    except auth_service.RegistrationError as error:
        record_audit_event(
            db,
            action="registration.provider",
            mobile_number=payload.mobile_number,
            ip_address=client_ip(request),
            success=False,
            metadata={"reason": str(error)},
        )
        raise

    record_audit_event(
        db,
        action="registration.provider",
        actor_user_id=result["user"].id,
        actor_role=result["user"].role,
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=True,
    )
    return success_response(serialize_auth_result(result), "Provider registration completed")


@router.post("/register/patient", status_code=status.HTTP_201_CREATED)
def register_patient(
    payload: PatientRegistration,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = auth_service.register_patient(
            db,
            payload,
            ip_address=client_ip(request),
        )
    except auth_service.RegistrationError as error:
        record_audit_event(
            db,
            action="registration.patient",
            mobile_number=payload.mobile_number,
            ip_address=client_ip(request),
            success=False,
            metadata={"reason": str(error)},
        )
        raise

    record_audit_event(
        db,
        action="registration.patient",
        actor_user_id=result["user"].id,
        actor_role=result["user"].role,
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=True,
        metadata={"consent_version": result["consent"].consent_version},
    )
    return success_response(serialize_auth_result(result), "Patient registration completed")


@router.post("/register/caregiver", status_code=status.HTTP_201_CREATED)
def register_caregiver(
    payload: CaregiverRegistration,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = auth_service.register_caregiver(db, payload)
    except auth_service.RegistrationError as error:
        record_audit_event(
            db,
            action="registration.caregiver",
            mobile_number=payload.mobile_number,
            ip_address=client_ip(request),
            success=False,
            metadata={"reason": str(error)},
        )
        raise

    record_audit_event(
        db,
        action="registration.caregiver",
        actor_user_id=result["user"].id,
        actor_role=result["user"].role,
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=True,
    )
    return success_response(serialize_auth_result(result), "Caregiver registration completed")


@router.post("/login")
def login(payload: MobileRequest, request: Request, db: Session = Depends(get_db)):
    try:
        result = auth_service.login(db, payload.mobile_number)
    except auth_service.RegistrationError as error:
        record_audit_event(
            db,
            action="login",
            mobile_number=payload.mobile_number,
            ip_address=client_ip(request),
            success=False,
            metadata={"reason": str(error)},
        )
        raise

    record_audit_event(
        db,
        action="login",
        actor_user_id=result["user"].id,
        actor_role=result["user"].role,
        mobile_number=payload.mobile_number,
        ip_address=client_ip(request),
        success=True,
    )
    return success_response(serialize_auth_result(result), "Login completed")


@router.post("/session/validate")
def validate(payload: SessionTokenRequest, request: Request, db: Session = Depends(get_db)):
    session = validate_session(db, payload.session_token)
    if session is None:
        record_audit_event(
            db,
            action="session.validate",
            ip_address=client_ip(request),
            success=False,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    record_audit_event(
        db,
        action="session.validate",
        actor_user_id=session.user.id,
        actor_role=session.user.role,
        mobile_number=session.user.mobile_number,
        ip_address=client_ip(request),
        success=True,
    )
    session._issued_session_token = payload.session_token
    return success_response(
        {
            "valid": True,
            "user": serialize_user(session.user),
            "session": serialize_session(session),
            "dashboard_route": auth_service.DASHBOARD_ROUTES[session.user.role],
        },
        "Session is valid",
    )


@router.post("/logout")
def logout_session(payload: SessionTokenRequest, request: Request, db: Session = Depends(get_db)):
    session = validate_session(db, payload.session_token)
    logged_out = logout(db, payload.session_token)
    record_audit_event(
        db,
        action="logout",
        actor_user_id=session.user.id if session else None,
        actor_role=session.user.role if session else None,
        mobile_number=session.user.mobile_number if session else None,
        ip_address=client_ip(request),
        success=logged_out,
    )
    return success_response({"logged_out": logged_out}, "Logged out")
