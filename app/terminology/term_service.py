from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.terminology import Term, TermTag


DEMO_TERMS = (
    ("demo_term_paracetamol", "Paracetamol", "medication"),
    ("demo_term_body_temperature", "Body Temperature", "measurement"),
    ("demo_term_blood_pressure", "Blood Pressure", "measurement"),
    ("demo_term_walking_exercise", "Walking Exercise", "recommendation"),
    ("demo_term_cbc", "CBC", "investigation"),
    ("demo_term_hba1c", "HbA1c", "investigation"),
    ("demo_term_dolo_650", "Dolo 650 mg oral tablet", "medication"),
    ("demo_term_temperature", "Temperature", "measurement"),
    ("demo_term_exercise", "Exercise", "recommendation"),
)
RESPONSE_REASON_TERMS = (
    ("422587007", "Nausea", "response_reason"),
    ("418290006", "Itching", "response_reason"),
    ("200892002", "Rashes", "response_reason"),
    ("422400008", "Vomiting", "response_reason"),
    ("16932000", "Nausea and vomiting", "response_reason"),
    ("62315008", "Diarrhoea", "response_reason"),
    ("74964007", "Other", "response_reason"),
)
SUPPORTED_TAGS = ("medication", "measurement", "recommendation", "investigation")

COMMON_OPTIONS = {
    "frequencies": [
        {"value": "once_daily", "label": "Once daily"},
        {"value": "twice_daily", "label": "Twice daily"},
        {"value": "three_times_daily", "label": "Three times daily"},
        {"value": "four_times_daily", "label": "Four times daily"},
        {"value": "every_4_hours", "label": "Every 4 hours"},
        {"value": "every_6_hours", "label": "Every 6 hours"},
        {"value": "weekly", "label": "Weekly"},
        {"value": "monthly", "label": "Monthly"},
        {"value": "as_needed", "label": "As needed"},
    ],
    "duration_units": ["hours", "days", "weeks", "months"],
    "notifications": ["immediate", "daily_summary", "both", "none"],
    "instruction_suggestions": [
        "With or after meals",
        "Before meals",
        "After resting for five minutes",
        "Follow the provider's safety instructions",
    ],
}

TAG_OPTIONS = {
    "medication": {
        "dose_units": ["mcg", "mg", "g", "mL", "tablet", "capsule", "drop", "puff", "unit"],
        "routes": ["oral", "topical", "inhaled", "injection", "other"],
    },
    "measurement": {
        "comparators": ["more_than", "less_than", "at_least", "at_most", "equal_to"],
    },
    "investigation": {"priorities": ["routine", "urgent", "asap", "stat"]},
    "recommendation": {},
}

TERM_OPTIONS = {
    "demo_term_body_temperature": {"measurement_units": ["°C", "°F"]},
    "demo_term_temperature": {"measurement_units": ["°C", "°F"]},
    "demo_term_blood_pressure": {"measurement_units": ["mmHg"]},
}

DRUG_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "svp_ide_drug_catalog_details_sample.json"


@lru_cache(maxsize=1)
def _drug_catalog():
    try:
        data = json.loads(DRUG_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Approved medication catalog could not be loaded") from error
    if not isinstance(data, dict):
        raise RuntimeError("Approved medication catalog must be a JSON object")
    return data


def seed_demo_terms(db: Session):
    changed = False
    catalog_terms = tuple(
        (concept_id, item["term"], "medication")
        for concept_id, item in _drug_catalog().items()
    )
    for concept_id, display_term, tag in (*DEMO_TERMS, *catalog_terms, *RESPONSE_REASON_TERMS):
        term = db.query(Term).options(joinedload(Term.tags)).filter(Term.concept_id == concept_id).first()
        if term is None:
            term = Term(concept_id=concept_id, term=display_term, language="en")
            db.add(term)
            changed = True
        elif term.term != display_term or term.language != "en":
            term.term = display_term
            term.language = "en"
            changed = True
        if tag not in {item.tag for item in term.tags}:
            term.tags.append(TermTag(tag=tag))
            changed = True
    if changed:
        db.commit()


def _serialize_term(term: Term):
    tag = term.tags[0].tag if term.tags else None
    return {"conceptId": term.concept_id, "term": term.term, "tag": tag}


def search_provider_terms(db: Session, *, query: str, tag: str | None = None, limit: int = 20):
    cleaned = query.strip()
    if len(cleaned) < 3:
        raise ValueError("Enter at least 3 characters to search")
    if len(cleaned) > 80:
        raise ValueError("Search query must be 80 characters or fewer")
    if tag is not None and tag not in SUPPORTED_TAGS:
        raise ValueError("Unsupported terminology tag")

    query_builder = db.query(Term).options(joinedload(Term.tags)).join(TermTag)
    query_builder = query_builder.filter(TermTag.tag.in_(SUPPORTED_TAGS))
    query_builder = query_builder.filter(
        or_(
            TermTag.tag != "medication",
            Term.concept_id.in_(tuple(_drug_catalog().keys())),
        )
    )
    query_builder = query_builder.filter(func.lower(Term.term).contains(cleaned.lower(), autoescape=True))
    if tag is not None:
        query_builder = query_builder.filter(TermTag.tag == tag)
    terms = query_builder.order_by(func.lower(Term.term)).limit(min(max(limit, 1), 20)).all()
    return [_serialize_term(term) for term in terms]


def resolve_provider_term(db: Session, *, concept_id: str, expected_term: str, expected_tag: str):
    term = db.query(Term).options(joinedload(Term.tags)).filter(Term.concept_id == concept_id).first()
    if term is None:
        raise ValueError("Selected clinical term is not in the approved terminology")
    tags = {tag.tag for tag in term.tags}
    if term.term != expected_term or expected_tag not in tags:
        raise ValueError("Clinical term, concept, and advisory type do not match")
    return _serialize_term(term)


def search_terms(db: Session, *, query: str, tag: str | None = None, limit: int = 20):
    return search_provider_terms(db, query=query, tag=tag, limit=limit)


def get_term(db: Session, *, concept_id: str):
    term = db.query(Term).options(joinedload(Term.tags)).filter(Term.concept_id == concept_id).first()
    if term is None:
        raise ValueError("Clinical term not found")
    return _serialize_term(term)


def get_tags(db: Session, *, concept_id: str):
    return get_term(db, concept_id=concept_id)["tag"]


def get_advisory_options(db: Session, *, concept_id: str):
    """Return the only values the API accepts for a selected approved term."""
    term = get_term(db, concept_id=concept_id)
    tag = term["tag"]
    options = {
        **COMMON_OPTIONS,
        **TAG_OPTIONS[tag],
        **TERM_OPTIONS.get(concept_id, {}),
    }
    catalog_item = _drug_catalog().get(concept_id)
    if tag == "medication" and catalog_item is None:
        raise ValueError("Medication is not in the approved drug catalogue")
    if catalog_item:
        dose_form = str(catalog_item.get("dose_form", "")).strip().lower()
        route = str(catalog_item.get("route", "")).strip().lower()
        if dose_form in TAG_OPTIONS["medication"]["dose_units"]:
            options["dose_units"] = [dose_form]
        if route in TAG_OPTIONS["medication"]["routes"]:
            options["routes"] = [route]
        options["medication_details"] = {
            "generic": catalog_item.get("generic"),
            "strength": catalog_item.get("strength"),
            "dose_form": catalog_item.get("dose_form"),
            "route": catalog_item.get("route"),
            "method": catalog_item.get("method"),
            "supplier_name": catalog_item.get("supplier_name"),
        }
    if tag == "measurement" and not options.get("measurement_units"):
        raise ValueError("The selected measurement has no approved unit metadata")
    return {"term": term, "options": options}


def search_response_reasons(db: Session, *, query: str | None = None, limit: int = 20):
    cleaned = (query or "").strip()
    if cleaned and len(cleaned) < 2:
        raise ValueError("Enter at least 2 characters to search response reasons")
    if len(cleaned) > 80:
        raise ValueError("Search query must be 80 characters or fewer")
    builder = db.query(Term).options(joinedload(Term.tags)).join(TermTag).filter(
        TermTag.tag == "response_reason"
    )
    if cleaned:
        builder = builder.filter(func.lower(Term.term).contains(cleaned.lower(), autoescape=True))
    terms = builder.order_by(func.lower(Term.term)).limit(min(max(limit, 1), 50)).all()
    return [
        {"conceptId": term.concept_id, "term": term.term, "tag": "response_reason"}
        for term in terms
    ]


def resolve_response_reason(db: Session, *, concept_id: str, term: str):
    record = db.query(Term).join(TermTag).filter(
        Term.concept_id == concept_id,
        Term.term == term,
        TermTag.tag == "response_reason",
    ).first()
    if record is None:
        raise ValueError("Missed-response reason must be selected from approved terminology")
    return {"conceptId": record.concept_id, "term": record.term, "tag": "response_reason"}
