PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;

DROP TABLE IF EXISTS term_tags;
DROP TABLE IF EXISTS concept_tags;
DROP TABLE IF EXISTS doseform_unit_options;
DROP TABLE IF EXISTS unit_doses;
DROP TABLE IF EXISTS dose_forms;
DROP TABLE IF EXISTS drug_ingredients;
DROP TABLE IF EXISTS drug_catalog;
DROP TABLE IF EXISTS allergy_causative_agents;
DROP TABLE IF EXISTS substance_ancestors;
DROP TABLE IF EXISTS terms_fts;
DROP TABLE IF EXISTS terms;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS source_files;

CREATE TABLE source_files (
  source_file_id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  bytes INTEGER,
  sha256 TEXT,
  loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE concepts (
  concept_id TEXT PRIMARY KEY
);

CREATE TABLE terms (
  term_id INTEGER PRIMARY KEY,
  concept_id TEXT NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  term_norm TEXT GENERATED ALWAYS AS (lower(trim(term))) STORED,
  UNIQUE (concept_id, term_norm)
);

CREATE TABLE tags (
  tag_id INTEGER PRIMARY KEY,
  tag TEXT NOT NULL,
  tag_norm TEXT GENERATED ALWAYS AS (lower(trim(tag))) STORED,
  UNIQUE (tag_norm)
);

CREATE TABLE concept_tags (
  concept_id TEXT NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
  PRIMARY KEY (concept_id, tag_id)
);

CREATE TABLE term_tags (
  term_id INTEGER NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
  PRIMARY KEY (term_id, tag_id)
);

CREATE TABLE drug_catalog (
  medication_concept_id TEXT PRIMARY KEY REFERENCES concepts(concept_id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  ingredient_count INTEGER,
  manufactured_df_concept_id TEXT,
  dose_form_concept_id TEXT,
  prescription_text TEXT,
  admin_instruction_text TEXT
);

CREATE TABLE drug_ingredients (
  medication_concept_id TEXT NOT NULL REFERENCES drug_catalog(medication_concept_id) ON DELETE CASCADE,
  ingredient_concept_id TEXT NOT NULL,
  ingredient_order INTEGER NOT NULL,
  PRIMARY KEY (medication_concept_id, ingredient_concept_id, ingredient_order)
);

CREATE TABLE allergy_causative_agents (
  allergy_concept_id TEXT NOT NULL,
  causative_agent_concept_id TEXT NOT NULL,
  PRIMARY KEY (allergy_concept_id, causative_agent_concept_id)
);

CREATE TABLE substance_ancestors (
  substance_concept_id TEXT NOT NULL,
  ancestor_concept_id TEXT NOT NULL,
  PRIMARY KEY (substance_concept_id, ancestor_concept_id)
);

CREATE TABLE dose_forms (
  form_concept_id TEXT PRIMARY KEY REFERENCES concepts(concept_id) ON DELETE CASCADE,
  form_term TEXT NOT NULL
);

CREATE TABLE unit_doses (
  unit_dose_id INTEGER PRIMARY KEY,
  unit_concept_id TEXT NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
  unit_term TEXT NOT NULL,
  unit_term_norm TEXT GENERATED ALWAYS AS (lower(trim(unit_term))) STORED,
  UNIQUE (unit_concept_id, unit_term_norm)
);

CREATE TABLE doseform_unit_options (
  form_concept_id TEXT NOT NULL REFERENCES dose_forms(form_concept_id) ON DELETE CASCADE,
  unit_concept_id TEXT NOT NULL,
  unit_term TEXT NOT NULL,
  display_order INTEGER NOT NULL,
  PRIMARY KEY (form_concept_id, unit_concept_id, unit_term)
);

CREATE VIRTUAL TABLE terms_fts USING fts5(
  term,
  concept_id UNINDEXED,
  content='terms',
  content_rowid='term_id',
  tokenize='unicode61 remove_diacritics 2'
);
