from __future__ import annotations

from typing import Any


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def diagnosis_columns(diagnosis: Any):
    if diagnosis is None:
        return {
            "diagnosis": None,
            "diagnosis_concept_id": None,
            "diagnosis_term": None,
            "diagnosis_notes": None,
        }
    if isinstance(diagnosis, str):
        cleaned = diagnosis.strip()
        return {
            "diagnosis": cleaned or None,
            "diagnosis_concept_id": None,
            "diagnosis_term": None,
            "diagnosis_notes": None,
        }
    concept_id = getattr(diagnosis, "conceptId", None)
    term = getattr(diagnosis, "term", None)
    notes = getattr(diagnosis, "notes", None)
    if concept_id is None and isinstance(diagnosis, dict):
        concept_id = diagnosis.get("conceptId") or diagnosis.get("concept_id")
        term = diagnosis.get("term")
        notes = diagnosis.get("notes")
    term = _clean_optional(term)
    return {
        "diagnosis": term,
        "diagnosis_concept_id": _clean_optional(concept_id),
        "diagnosis_term": term,
        "diagnosis_notes": _clean_optional(notes),
    }


def serialize_diagnosis(plan):
    if plan.diagnosis_concept_id or plan.diagnosis_term or plan.diagnosis_notes:
        return {
            "conceptId": plan.diagnosis_concept_id,
            "term": plan.diagnosis_term or plan.diagnosis,
            "notes": plan.diagnosis_notes,
        }
    return plan.diagnosis
