from dataclasses import dataclass
from typing import Iterable


SUPPORTED_ROLES = ("PROVIDER", "PATIENT", "CAREGIVER", "ADMIN")


@dataclass(frozen=True)
class Permission:
    code: str
    label: str


PERMISSIONS_MATRIX = {
    "PROVIDER": (
        Permission("VIEW_PATIENTS", "View Patients"),
        Permission("CREATE_CARE_PLANS", "Create Care Plans"),
        Permission("VIEW_TIMELINE", "View Timeline"),
        Permission("VIEW_ALERTS", "View Alerts"),
        Permission("REQUEST_PATIENT_ACCESS", "Request Patient Access"),
    ),
    "PATIENT": (
        Permission("VIEW_TASKS", "View Tasks"),
        Permission("RESPOND_TO_TASKS", "Respond To Tasks"),
        Permission("VIEW_TIMELINE", "View Timeline"),
        Permission("MANAGE_CONSENT", "Manage Consent"),
    ),
    "CAREGIVER": (
        Permission("VIEW_PATIENT_STATUS", "View Patient Status"),
        Permission("VIEW_TIMELINE", "View Timeline"),
        Permission("RECEIVE_NOTIFICATIONS", "Receive Notifications"),
        Permission("REQUEST_CAREGIVER_ACCESS", "Request Caregiver Access"),
    ),
    "ADMIN": (
        Permission("SYSTEM_ADMINISTRATION", "System Administration"),
    ),
}


def normalize_role(role: str):
    return role.upper() if role else ""


def get_role_permissions(role: str):
    normalized = normalize_role(role)
    return list(PERMISSIONS_MATRIX.get(normalized, ()))


def serialize_permissions(permissions: Iterable[Permission]):
    return [{"code": permission.code, "label": permission.label} for permission in permissions]


def has_permission(role: str, permission_code: str):
    normalized_code = permission_code.upper()
    return any(permission.code == normalized_code for permission in get_role_permissions(role))
