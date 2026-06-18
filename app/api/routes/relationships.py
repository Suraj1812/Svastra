from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip
from app.core.responses import success_response
from app.database import get_db
from app.models.consent import RelationshipConsent
from app.models.user import User
from app.rbac.permission_validator import authorize_request
from app.relationships.relationship_service import (
    create_patient_caregiver_link,
    create_provider_patient_link,
    deactivate_relationship,
    get_caregiver_patients,
    get_patient_caregivers,
    get_patient_providers,
    get_provider_patients,
    serialize_relationship,
)
from app.relationships.relationship_validator import (
    RelationshipValidationError,
    relationship_for_party,
)
from app.schemas.relationship import RelationshipCreateRequest


router = APIRouter(prefix="/relationships", tags=["Relationships"])


def _relationship_error(error: Exception):
    message = str(error)
    code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=code, detail=message) from error


def _include_inactive(status_filter: str):
    return status_filter == "ALL"


@router.get("/search")
def search_patient_for_relationship(
    mobile_number: str = Query(..., min_length=10, max_length=20),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permission = (
        "REQUEST_PATIENT_ACCESS"
        if current_user.role == "provider"
        else "REQUEST_CAREGIVER_ACCESS"
    )
    authorize_request(current_user, permission)
    patient = db.query(User).filter(
        User.mobile_number == mobile_number,
        User.role == "patient",
        User.is_active.is_(True),
    ).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active patient matched")
    consent_type = "provider_access" if current_user.role == "provider" else "caregiver_access"
    existing = db.query(RelationshipConsent).filter(
        RelationshipConsent.patient_id == patient.id,
        RelationshipConsent.requestor_id == current_user.id,
        RelationshipConsent.consent_type == consent_type,
        RelationshipConsent.status.in_(("PENDING", "ACTIVE")),
    ).first()
    return success_response(
        {
            "patient": {"id": patient.id, "full_name": patient.full_name},
            "consent_status": existing.status if existing else None,
        }
    )


@router.get("/providers")
def patient_providers(
    relationship_status: str = Query("ALL", alias="status", pattern="^(ACTIVE|INACTIVE|ALL)$"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role is required")
    links = get_patient_providers(
        db,
        patient_id=current_user.id,
        include_inactive=_include_inactive(relationship_status),
    )
    if relationship_status == "INACTIVE":
        links = [link for link in links if link.status == "ended"]
    return success_response(
        {"relationships": [serialize_relationship(link, viewer_id=current_user.id) for link in links]}
    )


@router.get("/caregivers")
def patient_caregivers(
    relationship_status: str = Query("ALL", alias="status", pattern="^(ACTIVE|INACTIVE|ALL)$"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role is required")
    links = get_patient_caregivers(
        db,
        patient_id=current_user.id,
        include_inactive=_include_inactive(relationship_status),
    )
    if relationship_status == "INACTIVE":
        links = [link for link in links if link.status == "ended"]
    return success_response(
        {"relationships": [serialize_relationship(link, viewer_id=current_user.id) for link in links]}
    )


@router.get("/patients")
def linked_patients(
    relationship_status: str = Query("ALL", alias="status", pattern="^(ACTIVE|INACTIVE|ALL)$"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "provider":
        links = get_provider_patients(
            db,
            provider_id=current_user.id,
            include_inactive=_include_inactive(relationship_status),
        )
    elif current_user.role == "caregiver":
        links = get_caregiver_patients(
            db,
            caregiver_id=current_user.id,
            include_inactive=_include_inactive(relationship_status),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider or caregiver role is required",
        )
    if relationship_status == "INACTIVE":
        links = [link for link in links if link.status == "ended"]
    return success_response(
        {"relationships": [serialize_relationship(link, viewer_id=current_user.id) for link in links]}
    )


@router.get("/linkable")
def linkable_patients(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    consent_type = {
        "provider": "provider_access",
        "caregiver": "caregiver_access",
    }.get(current_user.role)
    if consent_type is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider or caregiver role is required",
        )
    consents = db.query(RelationshipConsent).filter(
        RelationshipConsent.requestor_id == current_user.id,
        RelationshipConsent.consent_type == consent_type,
        RelationshipConsent.status == "ACTIVE",
    ).order_by(RelationshipConsent.granted_at.desc()).all()
    active_patient_ids = {
        relationship.patient_id
        for relationship in (
            get_provider_patients(db, provider_id=current_user.id, include_inactive=False)
            if current_user.role == "provider"
            else get_caregiver_patients(db, caregiver_id=current_user.id, include_inactive=False)
        )
    }
    return success_response(
        {
            "patients": [
                {
                    "patient": {
                        "id": consent.patient.id,
                        "full_name": consent.patient.full_name,
                    },
                    "consent_request_id": consent.id,
                    "consent_type": consent.consent_type,
                    "granted_at": consent.granted_at,
                }
                for consent in consents
                if consent.patient_id not in active_patient_ids
            ]
        }
    )


@router.post("/provider-patient", status_code=status.HTTP_201_CREATED)
def create_provider_relationship(
    payload: RelationshipCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider role is required")
    try:
        link, created = create_provider_patient_link(
            db,
            provider=current_user,
            patient_id=payload.patient_id,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except RelationshipValidationError as error:
        _relationship_error(error)
    return success_response(
        {**serialize_relationship(link, viewer_id=current_user.id), "created": created},
        "Provider-patient relationship created" if created else "Relationship already active",
    )


@router.post("/patient-caregiver", status_code=status.HTTP_201_CREATED)
def create_caregiver_relationship(
    payload: RelationshipCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "caregiver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caregiver role is required")
    try:
        link, created = create_patient_caregiver_link(
            db,
            caregiver=current_user,
            patient_id=payload.patient_id,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except RelationshipValidationError as error:
        _relationship_error(error)
    return success_response(
        {**serialize_relationship(link, viewer_id=current_user.id), "created": created},
        "Patient-caregiver relationship created" if created else "Relationship already active",
    )


@router.get("/{link_id}")
def relationship_detail(
    link_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        link = relationship_for_party(db, link_id=link_id, current_user=current_user)
    except RelationshipValidationError as error:
        _relationship_error(error)
    return success_response(
        serialize_relationship(link, viewer_id=current_user.id, include_mobile=True)
    )


@router.delete("/{link_id}")
def deactivate_healthcare_relationship(
    link_id: str,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        link, deactivated = deactivate_relationship(
            db,
            link_id=link_id,
            actor_user=current_user,
            ip_address=client_ip(request),
        )
    except RelationshipValidationError as error:
        _relationship_error(error)
    return success_response(
        {**serialize_relationship(link, viewer_id=current_user.id), "deactivated": deactivated},
        "Relationship deactivated" if deactivated else "Relationship already inactive",
    )
