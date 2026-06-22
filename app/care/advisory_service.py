from __future__ import annotations

import json

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.audit.audit_service import record_audit_event
from app.care.allergy_service import check_medication_allergies
from app.care.tag_resolver import resolve_tag
from app.models.care import Advisory, CarePlan
from app.models.user import User
from app.schemas.care import (
    InvestigationConfiguration,
    MeasurementConfiguration,
    MedicationConfiguration,
    RecommendationConfiguration,
)
from app.terminology.term_service import get_advisory_options


CONFIGURATION_MODELS = {
    "medication": MedicationConfiguration,
    "measurement": MeasurementConfiguration,
    "recommendation": RecommendationConfiguration,
    "investigation": InvestigationConfiguration,
}

def validate_advisory_configuration(
    db: Session, *, tag: str, concept_id: str, configuration: dict
):
    model = CONFIGURATION_MODELS.get(tag)
    if model is None:
        raise ValueError("Unsupported advisory type")
    try:
        validated = model.model_validate(configuration)
    except ValidationError as error:
        messages = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
        )
        raise ValueError(f"Invalid {tag} configuration: {messages}") from error

    options = get_advisory_options(db, concept_id=concept_id)["options"]
    if tag == "measurement":
        allowed_units = set(options["measurement_units"])
        if validated.measurement_unit not in allowed_units:
            raise ValueError(
                f"Measurement unit must be one of: {', '.join(sorted(allowed_units))}"
            )
    elif tag == "medication":
        if validated.dose_unit not in set(options["dose_units"]):
            raise ValueError(f"Dose unit must be one of: {', '.join(options['dose_units'])}")
        if validated.route not in set(options["routes"]):
            raise ValueError(f"Route must be one of: {', '.join(options['routes'])}")
    return validated.model_dump(mode="json", exclude_none=True)


def add_advisory(
    db: Session,
    *,
    care_plan: CarePlan,
    provider: User,
    concept_id: str,
    term: str,
    tag: str,
    configuration: dict,
    ip_address: str | None = None,
):
    if care_plan.provider_id != provider.id:
        raise PermissionError("Only the owning provider may edit this care plan")
    if care_plan.is_archived:
        raise ValueError("Archived care plans are read-only")
    resolve_tag(db, concept_id=concept_id, term=term, tag=tag)
    validated_configuration = validate_advisory_configuration(
        db,
        tag=tag,
        concept_id=concept_id,
        configuration=configuration,
    )
    if tag == "medication":
        medication_details = get_advisory_options(db, concept_id=concept_id)["options"][
            "medication_details"
        ]
        validated_configuration["allergy_warnings"] = check_medication_allergies(
            db,
            patient_id=care_plan.patient_id,
            medication_terms=[term, medication_details["generic"]],
        )
    duplicate = db.query(Advisory).filter(
        Advisory.care_plan_id == care_plan.id,
        Advisory.concept_id == concept_id,
        Advisory.advisory_type == tag,
    ).first()
    if duplicate is not None:
        raise ValueError("This advisory already exists in the care plan")

    advisory = Advisory(
        care_plan_id=care_plan.id,
        provider_id=provider.id,
        patient_id=care_plan.patient_id,
        advisory_type=tag,
        concept_id=concept_id,
        term=term,
        tag=tag,
        configuration_json=json.dumps(validated_configuration, sort_keys=True),
        status="DRAFT",
        execution_status="pending",
    )
    db.add(advisory)
    db.commit()
    db.refresh(advisory)
    record_audit_event(
        db,
        action="advisory.created",
        actor_user_id=provider.id,
        actor_role=provider.role,
        mobile_number=provider.mobile_number,
        ip_address=ip_address,
        metadata={
            "advisory_id": advisory.id,
            "care_plan_id": care_plan.id,
            "patient_id": care_plan.patient_id,
            "advisory_type": tag,
        },
    )
    return advisory


def serialize_advisory(advisory: Advisory):
    return {
        "id": advisory.id,
        "advisory_type": advisory.advisory_type,
        "term": advisory.term,
        "tag": advisory.tag,
        "configuration": json.loads(advisory.configuration_json),
        "allergy_warnings": json.loads(advisory.configuration_json).get("allergy_warnings", []),
        "status": advisory.status,
        "execution_status": advisory.execution_status,
        "published_at": advisory.published_at,
        "created_at": advisory.created_at,
    }
