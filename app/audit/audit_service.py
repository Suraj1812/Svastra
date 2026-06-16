import json

from sqlalchemy.orm import Session

from app.core.logging import audit_logger
from app.models.audit import AuditLog


def record_audit_event(
    db: Session,
    action: str,
    actor_user_id: int = None,
    actor_role: str = None,
    mobile_number: str = None,
    ip_address: str = None,
    success: bool = True,
    metadata: dict = None,
):
    event = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        mobile_number=mobile_number,
        ip_address=ip_address,
        success=success,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(event)
    db.commit()
    audit_logger.info(
        "action=%s actor_user_id=%s role=%s mobile=%s success=%s",
        action,
        actor_user_id,
        actor_role,
        mobile_number,
        success,
    )
    return event
