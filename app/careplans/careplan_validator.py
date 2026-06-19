from sqlalchemy.orm import Session

from app.models.user import User
from app.relationships.relationship_validator import has_active_provider_relationship


def validate_careplan_access(db: Session, *, provider: User, patient_id: int):
    if provider.role != "provider":
        raise PermissionError("Provider role is required")
    if not has_active_provider_relationship(
        db,
        provider_id=provider.id,
        patient_id=patient_id,
    ):
        raise PermissionError("Active provider-patient relationship is required")
    return True
