import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.allergy import PatientAllergy


def _normalise(value: str):
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def get_active_allergies(db: Session, *, patient_id: int):
    return db.query(PatientAllergy).filter(
        PatientAllergy.patient_id == patient_id,
        PatientAllergy.status == "ACTIVE",
    ).order_by(PatientAllergy.allergen_term).all()


def add_patient_allergy(db: Session, *, patient_id: int, allergen_term: str):
    existing = db.query(PatientAllergy).filter(
        PatientAllergy.patient_id == patient_id,
        func.lower(PatientAllergy.allergen_term) == allergen_term.lower(),
    ).first()
    if existing is not None:
        if existing.status == "INACTIVE":
            existing.status = "ACTIVE"
            db.commit()
            db.refresh(existing)
        return existing, False
    allergy = PatientAllergy(
        patient_id=patient_id,
        allergen_term=allergen_term,
        status="ACTIVE",
    )
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy, True


def check_medication_allergies(db: Session, *, patient_id: int, medication_term: str):
    medication = _normalise(medication_term)
    warnings = []
    for allergy in get_active_allergies(db, patient_id=patient_id):
        allergen = _normalise(allergy.allergen_term)
        if allergen and (allergen in medication or medication in allergen):
            warnings.append(
                {
                    "code": "POTENTIAL_ALLERGY",
                    "severity": "warning",
                    "message": f"Potential allergy conflict: {allergy.allergen_term}",
                    "allergen": allergy.allergen_term,
                    "blocking": False,
                }
            )
    return warnings


def serialize_allergy(allergy: PatientAllergy):
    return {
        "id": allergy.id,
        "allergen_term": allergy.allergen_term,
        "status": allergy.status,
        "created_at": allergy.created_at,
    }
