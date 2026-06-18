from sqlalchemy.orm import Session

from app.terminology.term_service import resolve_provider_term


def resolve_tag(db: Session, *, concept_id: str, term: str, tag: str):
    return resolve_provider_term(
        db,
        concept_id=concept_id,
        expected_term=term,
        expected_tag=tag,
    )
