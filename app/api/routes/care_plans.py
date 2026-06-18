from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip
from app.care.advisory_service import add_advisory, serialize_advisory
from app.care.care_plan_service import (
    create_care_plan,
    get_provider_care_plan,
    get_provider_care_plans,
    publish_care_plan,
    serialize_care_plan,
)
from app.core.responses import success_response
from app.database import get_db
from app.schemas.care import AdvisoryCreateRequest, CarePlanCreateRequest, PublishCarePlanRequest
from app.terminology.term_service import search_provider_terms


router = APIRouter(tags=["Care Plans"])


def _care_error(error: Exception):
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if "not found" in str(error).lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _require_provider(user):
    if user.role != "provider":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider role is required")


@router.get("/terminology/provider-terms")
def terminology_search(
    query: str = Query(..., min_length=3, max_length=80),
    tag: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=20),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        terms = search_provider_terms(db, query=query, tag=tag, limit=limit)
    except ValueError as error:
        _care_error(error)
    return success_response({"terms": terms, "query": query, "count": len(terms)})


@router.post("/care-plans", status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: CarePlanCreateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan = create_care_plan(
            db,
            provider=current_user,
            patient_id=payload.patient_id,
            title=payload.title,
            diagnosis=payload.diagnosis,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(serialize_care_plan(plan), "Care plan draft created")


@router.get("/care-plans")
def list_plans(
    patient_id: Optional[int] = Query(default=None, gt=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    plans = get_provider_care_plans(db, provider_id=current_user.id, patient_id=patient_id)
    return success_response({"care_plans": [serialize_care_plan(plan) for plan in plans]})


@router.get("/care-plans/{care_plan_id}")
def plan_detail(
    care_plan_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=current_user)
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(serialize_care_plan(plan))


@router.post("/care-plans/{care_plan_id}/advisories", status_code=status.HTTP_201_CREATED)
def create_advisory(
    care_plan_id: int,
    payload: AdvisoryCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan = get_provider_care_plan(db, care_plan_id=care_plan_id, provider=current_user)
        advisory = add_advisory(
            db,
            care_plan=plan,
            provider=current_user,
            concept_id=payload.concept_id,
            term=payload.term,
            tag=payload.tag,
            configuration=payload.configuration,
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(serialize_advisory(advisory), "Advisory added")


@router.post("/care-plans/{care_plan_id}/publish")
def publish_plan(
    care_plan_id: int,
    payload: PublishCarePlanRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan, event_id = publish_care_plan(
            db,
            care_plan_id=care_plan_id,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(
        {**serialize_care_plan(plan), "event_id": event_id},
        "Care plan published",
    )
