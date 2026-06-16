from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.consent.consent_service import get_patient_consent_status
from app.core.responses import success_response
from app.database import get_db
from app.rbac.rbac_service import get_role_permissions, serialize_permissions


router = APIRouter(prefix="/me", tags=["Current User"])


@router.get("/permissions")
def my_permissions(current_user=Depends(get_current_user)):
    permissions = get_role_permissions(current_user.role)
    return success_response(
        {
            "user_id": current_user.id,
            "role": current_user.role,
            "permissions": serialize_permissions(permissions),
        }
    )


@router.get("/consent-status")
def my_consent_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent status is available only for patients",
        )

    return success_response(get_patient_consent_status(db, current_user.id))
