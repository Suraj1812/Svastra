from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from app.models import allergy, audit, care, consent, postoffice, rbac, relationship, session, terminology, user  # noqa: F401
    from app.terminology.term_service import seed_demo_terms

    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()
    db = SessionLocal()
    try:
        seed_demo_terms(db)
    finally:
        db.close()


def _ensure_schema_compatibility():
    """Add non-destructive columns needed by older local SQLite MVP databases."""
    if engine.dialect.name != "sqlite" or "care_plans" not in inspect(engine).get_table_names():
        return
    columns = {column["name"] for column in inspect(engine).get_columns("care_plans")}
    with engine.begin() as connection:
        if "is_archived" not in columns:
            connection.execute(
                text("ALTER TABLE care_plans ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
            )
        if "archived_at" not in columns:
            connection.execute(text("ALTER TABLE care_plans ADD COLUMN archived_at DATETIME"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
