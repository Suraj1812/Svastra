from fastapi import HTTPException, status

from app.rbac.rbac_service import has_permission


def check_permission(role: str, permission_code: str):
    return has_permission(role, permission_code)


def authorize_request(user, permission_code: str):
    if not check_permission(user.role, permission_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
    return True
