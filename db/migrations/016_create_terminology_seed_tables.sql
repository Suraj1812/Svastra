PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS terms (
    concept_id TEXT PRIMARY KEY,
    term TEXT NOT NULL UNIQUE CHECK (length(trim(term)) > 0),
    language TEXT NOT NULL DEFAULT 'en' CHECK (length(trim(language)) > 0),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS term_tags (
    concept_id TEXT NOT NULL,
    tag TEXT NOT NULL CHECK (
        tag IN ('medication', 'measurement', 'recommendation', 'investigation')
    ),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (concept_id, tag),
    FOREIGN KEY (concept_id) REFERENCES terms(concept_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_terms_language_term ON terms(language, term);
CREATE INDEX IF NOT EXISTS idx_term_tags_tag ON term_tags(tag);
