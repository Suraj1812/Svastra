.bail on
.timer on

PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = OFF;
PRAGMA temp_store = MEMORY;

BEGIN;

INSERT OR REPLACE INTO source_files(path)
VALUES
  ('svp_entry_terms.json'),
  ('ide_drug_catalog_transformed.json'),
  ('doseform_unitdose_mapping.json'),
  ('allergy_causative_pairs.json'),
  ('substance_ancestors.json');

INSERT OR IGNORE INTO concepts(concept_id)
SELECT DISTINCT json_extract(value, '$.conceptId')
FROM json_each(readfile('svp_entry_terms.json'))
WHERE json_extract(value, '$.conceptId') IS NOT NULL;

INSERT OR IGNORE INTO tags(tag)
SELECT DISTINCT json_extract(value, '$.tag')
FROM json_each(readfile('svp_entry_terms.json'))
WHERE json_extract(value, '$.tag') IS NOT NULL
UNION
SELECT 'dose_form'
UNION
SELECT 'dose_unit';

INSERT OR IGNORE INTO terms(concept_id, term)
SELECT DISTINCT
  json_extract(value, '$.conceptId'),
  json_extract(value, '$.term')
FROM json_each(readfile('svp_entry_terms.json'))
WHERE json_extract(value, '$.conceptId') IS NOT NULL
  AND json_extract(value, '$.term') IS NOT NULL;

INSERT OR IGNORE INTO concept_tags(concept_id, tag_id)
SELECT DISTINCT
  json_extract(e.value, '$.conceptId'),
  tags.tag_id
FROM json_each(readfile('svp_entry_terms.json')) AS e
JOIN tags ON tags.tag_norm = lower(trim(json_extract(e.value, '$.tag')))
WHERE json_extract(e.value, '$.conceptId') IS NOT NULL
  AND json_extract(e.value, '$.tag') IS NOT NULL;

INSERT OR IGNORE INTO term_tags(term_id, tag_id)
SELECT DISTINCT
  terms.term_id,
  tags.tag_id
FROM json_each(readfile('svp_entry_terms.json')) AS e
JOIN terms
  ON terms.concept_id = json_extract(e.value, '$.conceptId')
 AND terms.term_norm = lower(trim(json_extract(e.value, '$.term')))
JOIN tags ON tags.tag_norm = lower(trim(json_extract(e.value, '$.tag')))
WHERE json_extract(e.value, '$.conceptId') IS NOT NULL
  AND json_extract(e.value, '$.term') IS NOT NULL
  AND json_extract(e.value, '$.tag') IS NOT NULL;

INSERT OR IGNORE INTO concepts(concept_id)
SELECT DISTINCT COALESCE(json_extract(value, '$.conceptId'), key)
FROM json_each(readfile('ide_drug_catalog_transformed.json'))
WHERE COALESCE(json_extract(value, '$.conceptId'), key) IS NOT NULL;

INSERT OR IGNORE INTO terms(concept_id, term)
SELECT DISTINCT
  COALESCE(json_extract(value, '$.conceptId'), key),
  json_extract(value, '$.term')
FROM json_each(readfile('ide_drug_catalog_transformed.json'))
WHERE COALESCE(json_extract(value, '$.conceptId'), key) IS NOT NULL
  AND json_extract(value, '$.term') IS NOT NULL;

INSERT OR IGNORE INTO concept_tags(concept_id, tag_id)
SELECT DISTINCT
  COALESCE(json_extract(e.value, '$.conceptId'), e.key),
  tags.tag_id
FROM json_each(readfile('ide_drug_catalog_transformed.json')) AS e
JOIN tags ON tags.tag_norm = 'medications'
WHERE COALESCE(json_extract(e.value, '$.conceptId'), e.key) IS NOT NULL;

INSERT OR IGNORE INTO term_tags(term_id, tag_id)
SELECT DISTINCT
  terms.term_id,
  tags.tag_id
FROM json_each(readfile('ide_drug_catalog_transformed.json')) AS e
JOIN terms
  ON terms.concept_id = COALESCE(json_extract(e.value, '$.conceptId'), e.key)
 AND terms.term_norm = lower(trim(json_extract(e.value, '$.term')))
JOIN tags ON tags.tag_norm = 'medications'
WHERE COALESCE(json_extract(e.value, '$.conceptId'), e.key) IS NOT NULL
  AND json_extract(e.value, '$.term') IS NOT NULL;

INSERT OR REPLACE INTO drug_catalog(
  medication_concept_id,
  term,
  ingredient_count,
  manufactured_df_concept_id,
  dose_form_concept_id,
  prescription_text,
  admin_instruction_text
)
SELECT
  COALESCE(json_extract(value, '$.conceptId'), key),
  json_extract(value, '$.term'),
  json_extract(value, '$.ingredient_count'),
  json_extract(value, '$.manufactured_df_conceptId'),
  json_extract(value, '$.dose_form_conceptId'),
  json_extract(value, '$.prescription_text'),
  json_extract(value, '$.admin_instruction_text')
FROM json_each(readfile('ide_drug_catalog_transformed.json'))
WHERE COALESCE(json_extract(value, '$.conceptId'), key) IS NOT NULL
  AND json_extract(value, '$.term') IS NOT NULL;

INSERT OR IGNORE INTO drug_ingredients(
  medication_concept_id,
  ingredient_concept_id,
  ingredient_order
)
SELECT DISTINCT
  COALESCE(drug.value ->> '$.conceptId', drug.key),
  ingredient.value,
  CAST(detail.key AS INTEGER)
FROM json_each(readfile('ide_drug_catalog_transformed.json')) AS drug
JOIN json_each(drug.value, '$.strength_details') AS detail
JOIN json_each(detail.value, '$.ingredient_conceptIds') AS ingredient
WHERE COALESCE(drug.value ->> '$.conceptId', drug.key) IS NOT NULL
  AND ingredient.value IS NOT NULL;

INSERT OR IGNORE INTO concepts(concept_id)
SELECT DISTINCT json_extract(value, '$.formConceptId')
FROM json_each(readfile('doseform_unitdose_mapping.json'))
WHERE json_extract(value, '$.formConceptId') IS NOT NULL
UNION
SELECT DISTINCT unit.value ->> '$.conceptId'
FROM json_each(readfile('doseform_unitdose_mapping.json')) AS form
JOIN json_each(form.value, '$.unitOptions') AS unit
WHERE unit.value ->> '$.conceptId' IS NOT NULL;

INSERT OR IGNORE INTO terms(concept_id, term)
SELECT DISTINCT
  json_extract(value, '$.formConceptId'),
  json_extract(value, '$.formTerm')
FROM json_each(readfile('doseform_unitdose_mapping.json'))
WHERE json_extract(value, '$.formConceptId') IS NOT NULL
  AND json_extract(value, '$.formTerm') IS NOT NULL
UNION
SELECT DISTINCT
  unit.value ->> '$.conceptId',
  unit.value ->> '$.term'
FROM json_each(readfile('doseform_unitdose_mapping.json')) AS form
JOIN json_each(form.value, '$.unitOptions') AS unit
WHERE unit.value ->> '$.conceptId' IS NOT NULL
  AND unit.value ->> '$.term' IS NOT NULL;

INSERT OR IGNORE INTO dose_forms(form_concept_id, form_term)
SELECT DISTINCT
  json_extract(value, '$.formConceptId'),
  json_extract(value, '$.formTerm')
FROM json_each(readfile('doseform_unitdose_mapping.json'))
WHERE json_extract(value, '$.formConceptId') IS NOT NULL
  AND json_extract(value, '$.formTerm') IS NOT NULL;

INSERT OR IGNORE INTO unit_doses(unit_concept_id, unit_term)
SELECT DISTINCT
  unit.value ->> '$.conceptId',
  unit.value ->> '$.term'
FROM json_each(readfile('doseform_unitdose_mapping.json')) AS form
JOIN json_each(form.value, '$.unitOptions') AS unit
WHERE unit.value ->> '$.conceptId' IS NOT NULL
  AND unit.value ->> '$.term' IS NOT NULL;

INSERT OR IGNORE INTO doseform_unit_options(
  form_concept_id,
  unit_concept_id,
  unit_term,
  display_order
)
SELECT DISTINCT
  form.value ->> '$.formConceptId',
  unit.value ->> '$.conceptId',
  unit.value ->> '$.term',
  CAST(unit.key AS INTEGER)
FROM json_each(readfile('doseform_unitdose_mapping.json')) AS form
JOIN json_each(form.value, '$.unitOptions') AS unit
WHERE form.value ->> '$.formConceptId' IS NOT NULL
  AND unit.value ->> '$.conceptId' IS NOT NULL
  AND unit.value ->> '$.term' IS NOT NULL;

INSERT OR IGNORE INTO concept_tags(concept_id, tag_id)
SELECT form_concept_id, tags.tag_id
FROM dose_forms
JOIN tags ON tags.tag_norm = 'dose_form';

INSERT OR IGNORE INTO concept_tags(concept_id, tag_id)
SELECT unit_concept_id, tags.tag_id
FROM unit_doses
JOIN tags ON tags.tag_norm = 'dose_unit';

INSERT OR IGNORE INTO term_tags(term_id, tag_id)
SELECT terms.term_id, tags.tag_id
FROM dose_forms
JOIN terms ON terms.concept_id = dose_forms.form_concept_id
JOIN tags ON tags.tag_norm = 'dose_form';

INSERT OR IGNORE INTO term_tags(term_id, tag_id)
SELECT terms.term_id, tags.tag_id
FROM unit_doses
JOIN terms ON terms.concept_id = unit_doses.unit_concept_id
JOIN tags ON tags.tag_norm = 'dose_unit';

INSERT OR IGNORE INTO allergy_causative_agents(
  allergy_concept_id,
  causative_agent_concept_id
)
SELECT DISTINCT
  json_extract(value, '$.allergy_conceptId'),
  json_extract(value, '$.causative_agent_conceptId')
FROM json_each(readfile('allergy_causative_pairs.json'))
WHERE json_extract(value, '$.allergy_conceptId') IS NOT NULL
  AND json_extract(value, '$.causative_agent_conceptId') IS NOT NULL;

INSERT OR IGNORE INTO substance_ancestors(
  substance_concept_id,
  ancestor_concept_id
)
SELECT DISTINCT
  ancestors.key,
  ancestor.value
FROM json_each(readfile('substance_ancestors.json')) AS ancestors
JOIN json_each(ancestors.value) AS ancestor
WHERE ancestors.key IS NOT NULL
  AND ancestor.value IS NOT NULL;

COMMIT;

PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_terms_concept_id ON terms(concept_id);
CREATE INDEX IF NOT EXISTS idx_terms_term_norm ON terms(term_norm);
CREATE INDEX IF NOT EXISTS idx_tags_tag_norm ON tags(tag_norm);
CREATE INDEX IF NOT EXISTS idx_concept_tags_tag_concept ON concept_tags(tag_id, concept_id);
CREATE INDEX IF NOT EXISTS idx_concept_tags_concept_tag ON concept_tags(concept_id, tag_id);
CREATE INDEX IF NOT EXISTS idx_term_tags_tag_term ON term_tags(tag_id, term_id);
CREATE INDEX IF NOT EXISTS idx_term_tags_term_tag ON term_tags(term_id, tag_id);
CREATE INDEX IF NOT EXISTS idx_drug_catalog_dose_form ON drug_catalog(dose_form_concept_id);
CREATE INDEX IF NOT EXISTS idx_drug_ingredients_ingredient ON drug_ingredients(ingredient_concept_id);
CREATE INDEX IF NOT EXISTS idx_allergy_causative_agent ON allergy_causative_agents(causative_agent_concept_id);
CREATE INDEX IF NOT EXISTS idx_substance_ancestors_ancestor ON substance_ancestors(ancestor_concept_id, substance_concept_id);
CREATE INDEX IF NOT EXISTS idx_doseform_unit_options_form ON doseform_unit_options(form_concept_id, display_order);
CREATE INDEX IF NOT EXISTS idx_doseform_unit_options_unit ON doseform_unit_options(unit_concept_id);

INSERT INTO terms_fts(rowid, term, concept_id)
SELECT
  terms.term_id,
  terms.term,
  terms.concept_id
FROM terms
GROUP BY terms.term_id;

PRAGMA optimize;
