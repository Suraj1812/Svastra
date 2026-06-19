import json

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.care.tag_resolver import resolve_tag
from app.care.allergy_service import check_medication_allergies
from app.models.care import Advisory, CarePlan
from app.models.user import User
from app.schemas.care import (
    InvestigationConfiguration,
    MeasurementConfiguration,
    MedicationConfiguration,
    RecommendationConfiguration,
)


CONFIGURATION_MODELS = {
    "medication": MedicationConfiguration,
    "measurement": MeasurementConfiguration,
    "recommendation": RecommendationConfiguration,
    "investigation": InvestigationConfiguration,
}

ALLOWED_MEASUREMENT_UNITS = {
    "demo_term_temperature": {"°C", "°F"},
    "demo_term_body_temperature": {"°C", "°F"},
    "demo_term_blood_pressure": {"mmHg"},
}


def validate_advisory_configuration(*, tag: str, concept_id: str, configuration: dict):
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

    if tag == "measurement":
        allowed_units = ALLOWED_MEASUREMENT_UNITS.get(concept_id)
        if allowed_units and validated.measurement_unit not in allowed_units:
            raise ValueError(
                f"Measurement unit must be one of: {', '.join(sorted(allowed_units))}"
            )
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
):
    if care_plan.provider_id != provider.id:
        raise PermissionError("Only the owning provider may edit this care plan")
    if care_plan.is_archived:
        raise ValueError("Archived care plans are read-only")
    resolve_tag(db, concept_id=concept_id, term=term, tag=tag)
    validated_configuration = validate_advisory_configuration(
        tag=tag,
        concept_id=concept_id,
        configuration=configuration,
    )
    if tag == "medication":
        validated_configuration["allergy_warnings"] = check_medication_allergies(
            db,
            patient_id=care_plan.patient_id,
            medication_term=term,
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
    )
    db.add(advisory)
    db.commit()
    db.refresh(advisory)
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
        "published_at": advisory.published_at,
        "created_at": advisory.created_at,
    }
