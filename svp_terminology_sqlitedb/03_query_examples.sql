-- Autocomplete/autosuggest by token prefix under one tag.
-- Bind :query_prefix without the trailing *, for example fever or para.
-- Bind :tag, for example diseases, findings, medications, investigation.
SELECT DISTINCT
  terms.term,
  terms.concept_id AS conceptId,
  tags.tag
FROM terms_fts
JOIN terms ON terms.term_id = terms_fts.rowid
JOIN term_tags ON term_tags.term_id = terms.term_id
JOIN tags ON tags.tag_id = term_tags.tag_id
WHERE terms_fts MATCH (:query_prefix || '*')
  AND tags.tag_norm = lower(trim(:tag))
ORDER BY rank
LIMIT 25;

-- Contains fallback when the UI must match characters inside a term.
-- This is less index-friendly than FTS prefix search, so keep LIMIT small.
SELECT DISTINCT
  terms.term,
  terms.concept_id AS conceptId,
  tags.tag
FROM terms
JOIN term_tags ON term_tags.term_id = terms.term_id
JOIN tags ON tags.tag_id = term_tags.tag_id
WHERE terms.term_norm LIKE ('%' || lower(trim(:characters)) || '%')
  AND tags.tag_norm = lower(trim(:tag))
ORDER BY
  CASE WHEN terms.term_norm LIKE (lower(trim(:characters)) || '%') THEN 0 ELSE 1 END,
  length(terms.term),
  terms.term_norm
LIMIT 25;

-- Return all terms and tags for a selected conceptId.
SELECT
  terms.term,
  terms.concept_id AS conceptId,
  tags.tag
FROM terms
LEFT JOIN term_tags ON term_tags.term_id = terms.term_id
LEFT JOIN tags ON tags.tag_id = term_tags.tag_id
WHERE terms.concept_id = :concept_id
ORDER BY tags.tag_norm, terms.term_norm;

-- Find unit dose options for a medication conceptId.
SELECT
  drug_catalog.medication_concept_id AS medicationConceptId,
  drug_catalog.term AS medicationTerm,
  drug_catalog.dose_form_concept_id AS doseFormConceptId,
  dose_forms.form_term AS doseFormTerm,
  doseform_unit_options.unit_term AS unitDoseTerm,
  doseform_unit_options.unit_concept_id AS unitDoseConceptId
FROM drug_catalog
JOIN dose_forms
  ON dose_forms.form_concept_id = drug_catalog.dose_form_concept_id
JOIN doseform_unit_options
  ON doseform_unit_options.form_concept_id = dose_forms.form_concept_id
WHERE drug_catalog.medication_concept_id = :medication_concept_id
ORDER BY doseform_unit_options.display_order, doseform_unit_options.unit_term;

-- Allergy check for one medication against a caller-supplied temporary table.
-- Before running this query, create and populate selected_drug_allergies:
--
-- CREATE TEMP TABLE selected_drug_allergies(allergy_concept_id TEXT PRIMARY KEY);
-- INSERT INTO selected_drug_allergies VALUES ('293611008'), ('...');
--
-- The check is positive if any medication ingredient is equivalent to or a
-- subtype of any causative agent linked to any selected allergy concept.
SELECT EXISTS (
  SELECT 1
  FROM drug_ingredients
  JOIN selected_drug_allergies ON 1 = 1
  JOIN allergy_causative_agents
    ON allergy_causative_agents.allergy_concept_id = selected_drug_allergies.allergy_concept_id
  LEFT JOIN substance_ancestors
    ON substance_ancestors.substance_concept_id = drug_ingredients.ingredient_concept_id
   AND substance_ancestors.ancestor_concept_id = allergy_causative_agents.causative_agent_concept_id
  WHERE drug_ingredients.medication_concept_id = :medication_concept_id
    AND (
      drug_ingredients.ingredient_concept_id = allergy_causative_agents.causative_agent_concept_id
      OR substance_ancestors.ancestor_concept_id IS NOT NULL
    )
) AS allergyCheckIsTrue;

-- Explain why the allergy check is true.
SELECT DISTINCT
  drug_ingredients.medication_concept_id AS medicationConceptId,
  medication_terms.term AS medicationTerm,
  drug_ingredients.ingredient_concept_id AS ingredientConceptId,
  ingredient_terms.term AS ingredientTerm,
  allergy_causative_agents.allergy_concept_id AS allergyConceptId,
  allergy_terms.term AS allergyTerm,
  allergy_causative_agents.causative_agent_concept_id AS causativeAgentConceptId,
  causative_terms.term AS causativeAgentTerm
FROM drug_ingredients
JOIN selected_drug_allergies
JOIN allergy_causative_agents
  ON allergy_causative_agents.allergy_concept_id = selected_drug_allergies.allergy_concept_id
LEFT JOIN substance_ancestors
  ON substance_ancestors.substance_concept_id = drug_ingredients.ingredient_concept_id
 AND substance_ancestors.ancestor_concept_id = allergy_causative_agents.causative_agent_concept_id
LEFT JOIN terms AS medication_terms
  ON medication_terms.concept_id = drug_ingredients.medication_concept_id
LEFT JOIN terms AS ingredient_terms
  ON ingredient_terms.concept_id = drug_ingredients.ingredient_concept_id
LEFT JOIN terms AS allergy_terms
  ON allergy_terms.concept_id = allergy_causative_agents.allergy_concept_id
LEFT JOIN terms AS causative_terms
  ON causative_terms.concept_id = allergy_causative_agents.causative_agent_concept_id
WHERE drug_ingredients.medication_concept_id = :medication_concept_id
  AND (
    drug_ingredients.ingredient_concept_id = allergy_causative_agents.causative_agent_concept_id
    OR substance_ancestors.ancestor_concept_id IS NOT NULL
  )
ORDER BY allergy_terms.term_norm, ingredient_terms.term_norm;

-- Tag inventory for UI control routing.
SELECT
  tags.tag,
  COUNT(DISTINCT concept_tags.concept_id) AS conceptCount,
  COUNT(DISTINCT term_tags.term_id) AS termCount
FROM tags
LEFT JOIN concept_tags ON concept_tags.tag_id = tags.tag_id
LEFT JOIN term_tags ON term_tags.tag_id = tags.tag_id
GROUP BY tags.tag_id
ORDER BY tags.tag_norm;
