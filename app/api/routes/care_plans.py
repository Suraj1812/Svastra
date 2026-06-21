from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip
from app.care.advisory_service import add_advisory, serialize_advisory
from app.care.allergy_service import add_patient_allergy, get_active_allergies, serialize_allergy
from app.care.care_plan_service import (
    create_care_plan,
    archive_care_plan,
    get_provider_care_plan,
    get_provider_care_plans,
    publish_care_plan,
    publish_advisory,
    serialize_care_plan,
    update_care_plan,
)
from app.core.responses import success_response
from app.database import get_db
from app.models.care import Advisory
from app.schemas.care import (
    AdvisoryCreateRequest,
    AllergyCreateRequest,
    CarePlanCreateRequest,
    CarePlanUpdateRequest,
    PublishCarePlanRequest,
)
from app.terminology.term_service import get_advisory_options, get_term, search_provider_terms


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


@router.get("/terminology/provider-terms/{concept_id}")
def terminology_detail(
    concept_id: str = Path(
        ..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        term = get_term(db, concept_id=concept_id)
    except ValueError as error:
        _care_error(error)
    return success_response(term)


@router.get("/terminology/provider-terms/{concept_id}/advisory-options")
def terminology_advisory_options(
    concept_id: str = Path(
        ..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    ),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        result = get_advisory_options(db, concept_id=concept_id)
    except ValueError as error:
        _care_error(error)
    return success_response(result)


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


@router.put("/care-plans/{care_plan_id}")
def update_plan(
    care_plan_id: int,
    payload: CarePlanUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan = update_care_plan(
            db,
            care_plan_id=care_plan_id,
            provider=current_user,
            title=payload.title,
            diagnosis=payload.diagnosis,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(serialize_care_plan(plan), "Care plan updated")


@router.delete("/care-plans/{care_plan_id}")
def archive_plan(
    care_plan_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        plan, archived = archive_care_plan(
            db,
            care_plan_id=care_plan_id,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(
        {**serialize_care_plan(plan), "archived": archived},
        "Care plan archived" if archived else "Care plan already archived",
    )


@router.post("/care-plans/{care_plan_id}/advisories", status_code=status.HTTP_201_CREATED)
def create_advisory(
    care_plan_id: int,
    payload: AdvisoryCreateRequest,
    request: Request,
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
            ip_address=client_ip(request),
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
        plan, deliveries = publish_care_plan(
            db,
            care_plan_id=care_plan_id,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(
        {
            **serialize_care_plan(plan),
            "event_id": deliveries[0]["event_id"],
            "event_ids": [item["event_id"] for item in deliveries],
            "deliveries": deliveries,
        },
        "Care plan published",
    )


@router.post("/care-plans/{care_plan_id}/advisories/{advisory_id}/publish")
def publish_one_advisory(
    care_plan_id: int,
    advisory_id: int,
    payload: PublishCarePlanRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_provider(current_user)
    try:
        advisory, event_id, acknowledgement = publish_advisory(
            db,
            care_plan_id=care_plan_id,
            advisory_id=advisory_id,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _care_error(error)
    return success_response(
        {
            "advisory": serialize_advisory(advisory),
            "event_id": event_id,
            "acknowledgement": acknowledgement,
        },
        "Advisory published, routed, and acknowledged",
    )


def _patient_instruction(advisory: Advisory):
    data = serialize_advisory(advisory)
    configuration = data["configuration"]
    duration = f"{configuration.get('duration_value')} {configuration.get('duration_unit')}"
    frequency = str(configuration.get("frequency", "")).replace("_", " ")
    if advisory.advisory_type == "medication":
        dose_value = configuration.get("dose_value")
        if isinstance(dose_value, float) and dose_value.is_integer():
            dose_value = int(dose_value)
        dose = configuration.get("dose") or (
            f"{dose_value} {configuration.get('dose_unit')}"
        )
        instruction = (
            f"Take {dose} by {configuration.get('route')} route, "
            f"{frequency}, for {duration}."
        )
    elif advisory.advisory_type == "measurement":
        instruction = (
            f"Record {advisory.term} in {configuration.get('measurement_unit')} "
            f"({frequency}) for {duration}."
        )
        if configuration.get("target_value") is not None:
            instruction = f"{instruction} Target: {configuration.get('target_value')}."
    elif advisory.advisory_type == "recommendation":
        recommendation = configuration.get("instruction") or advisory.term
        instruction = f"{recommendation} ({frequency}) for {duration}."
    else:
        instruction = (
            f"Complete {advisory.term} with {configuration.get('priority')} priority "
            f"({frequency}) for {duration}."
        )
    additional = configuration.get("additional_instructions")
    if additional:
        instruction = f"{instruction} {additional}"
    return {
        "id": advisory.id,
        "advisory_type": advisory.advisory_type,
        "advisory": advisory.term,
        "instruction": instruction,
        "status": advisory.status,
        "execution_status": advisory.execution_status,
        "created_at": advisory.created_at,
        "published_at": advisory.published_at,
        "care_plan": {
            "id": advisory.care_plan.id,
            "title": advisory.care_plan.title,
            "status": "INACTIVE" if advisory.care_plan.is_archived else advisory.care_plan.status,
        },
    }


@router.get("/me/advisories")
def my_advisories(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role is required")
    advisories = db.query(Advisory).filter(
        Advisory.patient_id == current_user.id,
        Advisory.status == "PUBLISHED",
    ).order_by(Advisory.published_at.desc()).all()
    return success_response({"advisories": [_patient_instruction(item) for item in advisories]})


@router.get("/me/allergies")
def my_allergies(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role is required")
    allergies = get_active_allergies(db, patient_id=current_user.id)
    return success_response({"allergies": [serialize_allergy(item) for item in allergies]})


@router.post("/me/allergies", status_code=status.HTTP_201_CREATED)
def add_my_allergy(
    payload: AllergyCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient role is required")
    allergy, created = add_patient_allergy(
        db,
        patient_id=current_user.id,
        allergen_term=payload.allergen_term,
    )
    return success_response(
        {**serialize_allergy(allergy), "created": created},
        "Allergy added" if created else "Allergy already recorded",
    )
