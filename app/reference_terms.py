import json
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.config import settings


REFERENCE_TERM_KEYS = ("conceptId", "term", "tag")


@lru_cache(maxsize=1)
def reference_terms() -> List[Dict[str, str]]:
    if not settings.reference_terms_path.exists():
        return []

    with settings.reference_terms_path.open(encoding="utf-8") as terms_file:
        data = json.load(terms_file)

    if isinstance(data, dict):
        terms = []
        for tag, values in data.items():
            for value in values:
                if isinstance(value, dict):
                    concept_id = value.get("conceptId")
                    term = value.get("term") or value.get("value")
                else:
                    concept_id = str(value)
                    term = str(value)
                if concept_id and term:
                    terms.append({"conceptId": str(concept_id), "term": str(term), "tag": str(tag)})
        return terms

    return [
        {
            "conceptId": str(item["conceptId"]),
            "term": str(item["term"]),
            "tag": str(item["tag"]),
        }
        for item in data
        if all(key in item for key in REFERENCE_TERM_KEYS)
    ]


def reference_terms_by_tag(tag: str):
    return [term for term in reference_terms() if term["tag"] == tag]


def get_reference_term(tag: str, term: str):
    for reference_term in reference_terms_by_tag(tag):
        if reference_term["term"] == term:
            return dict(reference_term)
    return None


def normalize_reference_term(value: Any):
    if hasattr(value, "model_dump"):
        value = value.model_dump()

    if not isinstance(value, dict):
        raise ValueError("Reference term must include conceptId, term, and tag")

    try:
        normalized = {
            "conceptId": str(value["conceptId"]).strip(),
            "term": str(value["term"]).strip(),
            "tag": str(value["tag"]).strip(),
        }
    except KeyError as error:
        raise ValueError("Reference term must include conceptId, term, and tag") from error

    if not all(normalized.values()):
        raise ValueError("Reference term fields cannot be empty")
    return normalized


def validate_reference_term(tag: str, value: Any):
    normalized = normalize_reference_term(value)
    if normalized["tag"] != tag:
        raise ValueError(f"Reference term tag must be {tag}")

    allowed_terms = reference_terms_by_tag(tag)
    if allowed_terms and normalized not in allowed_terms:
        allowed = ", ".join(term["term"] for term in allowed_terms)
        raise ValueError(f"Allowed {tag} values: {allowed}")
    return normalized


def encode_reference_term(value: Any):
    if value is None:
        return None
    return json.dumps(normalize_reference_term(value), sort_keys=True)


def decode_reference_term(value: Any, tag: Optional[str] = None):
    if value is None:
        return None

    if isinstance(value, dict):
        return validate_reference_term(tag, value) if tag else normalize_reference_term(value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.startswith("{"):
            decoded = json.loads(stripped)
            return validate_reference_term(tag, decoded) if tag else normalize_reference_term(decoded)
        if tag:
            legacy_term = get_reference_term(tag, stripped)
            if legacy_term is not None:
                return legacy_term

    raise ValueError("Stored reference term is invalid")
