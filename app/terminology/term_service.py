from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.terminology import Term, TermTag


DEMO_TERMS = (
    ("demo_term_dolo_650", "Dolo 650 mg oral tablet", "medication"),
    ("demo_term_temperature", "Temperature", "measurement"),
    ("demo_term_exercise", "Exercise", "recommendation"),
    ("demo_term_hba1c", "HbA1c", "investigation"),
)
SUPPORTED_TAGS = ("medication", "measurement", "recommendation", "investigation")


def seed_demo_terms(db: Session):
    changed = False
    for concept_id, display_term, tag in DEMO_TERMS:
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
