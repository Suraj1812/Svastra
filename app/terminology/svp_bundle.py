from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Iterable

from app.config import settings


_SAFE_CONCEPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_BUNDLE_TO_PROVIDER_TAG = {
    "investigation": "investigation",
}
SVP_ENTRY_TERMS_PATH = settings.terminology_bundle_entry_terms_path


def _clean_text(value: object, *, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or len(cleaned) > max_length:
        return None
    return cleaned


@lru_cache(maxsize=1)
def _load_svp_provider_terms() -> tuple[dict[str, str], ...]:
    """Load safe provider-authoring terms from the optional SVP terminology bundle.

    The full bundle contains diagnosis, allergy, medication and other reference
    tags. For the MVP authoring API we only expose tags that are already safely
    supported by advisory configuration validation. Medication remains restricted
    to the approved drug catalogue in term_service.py.
    """

    path = SVP_ENTRY_TERMS_PATH
    if not path.exists():
        return ()
    try:
        raw_terms = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("SVP terminology entry-term bundle could not be loaded") from error
    if not isinstance(raw_terms, list):
        raise RuntimeError("SVP terminology entry-term bundle must be a JSON array")

    terms: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw_terms:
        if not isinstance(item, dict):
            continue
        tag = _BUNDLE_TO_PROVIDER_TAG.get(str(item.get("tag", "")).strip())
        if tag is None:
            continue
        concept_id = _clean_text(item.get("conceptId"), max_length=64)
        term = _clean_text(item.get("term"), max_length=255)
        if concept_id is None or term is None or not _SAFE_CONCEPT_ID.match(concept_id):
            continue
        key = (concept_id, term, tag)
        if key in seen:
            continue
        seen.add(key)
        terms.append({"conceptId": concept_id, "term": term, "tag": tag})
    return tuple(terms)


@lru_cache(maxsize=1)
def _svp_terms_by_concept() -> dict[str, tuple[dict[str, str], ...]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for term in _load_svp_provider_terms():
        grouped.setdefault(term["conceptId"], []).append(term)
    return {concept_id: tuple(items) for concept_id, items in grouped.items()}


def svp_bundle_available() -> bool:
    return SVP_ENTRY_TERMS_PATH.exists()


def search_svp_provider_terms(
    *,
    query: str,
    tag: str | None = None,
    limit: int = 20,
    excluded_concept_ids: Iterable[str] = (),
):
    if tag is not None and tag not in set(_BUNDLE_TO_PROVIDER_TAG.values()):
        return []
    cleaned = query.strip().lower()
    if len(cleaned) < 3:
        return []
    excluded = set(excluded_concept_ids)
    matches = [
        term
        for term in _load_svp_provider_terms()
        if term["conceptId"] not in excluded
        and (tag is None or term["tag"] == tag)
        and cleaned in term["term"].lower()
    ]
    matches.sort(
        key=lambda term: (
            0 if term["term"].lower().startswith(cleaned) else 1,
            len(term["term"]),
            term["term"].lower(),
            term["conceptId"],
        )
    )
    return matches[: min(max(limit, 1), 20)]


def find_svp_provider_term(
    *,
    concept_id: str,
    expected_term: str | None = None,
    expected_tag: str | None = None,
):
    if expected_tag is not None and expected_tag not in set(_BUNDLE_TO_PROVIDER_TAG.values()):
        return None
    for term in _svp_terms_by_concept().get(concept_id, ()):
        if expected_tag is not None and term["tag"] != expected_tag:
            continue
        if expected_term is not None and term["term"] != expected_term:
            continue
        return term
    return None
