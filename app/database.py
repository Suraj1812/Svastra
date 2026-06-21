import json
from hashlib import sha256

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
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "care_plans" in tables:
            columns = {column["name"] for column in inspector.get_columns("care_plans")}
            if "is_archived" not in columns:
                connection.execute(
                    text("ALTER TABLE care_plans ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
                )
            if "archived_at" not in columns:
                connection.execute(text("ALTER TABLE care_plans ADD COLUMN archived_at DATETIME"))

        if "advisories" in tables:
            columns = {column["name"] for column in inspector.get_columns("advisories")}
            if "execution_status" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE advisories ADD COLUMN execution_status "
                        "VARCHAR(20) NOT NULL DEFAULT 'pending'"
                    )
                )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_advisories_execution_status "
                    "ON advisories(execution_status)"
                )
            )

        if "timeline_events" in tables:
            columns = {column["name"] for column in inspector.get_columns("timeline_events")}
            if "payload_sha256" not in columns:
                connection.execute(text("ALTER TABLE timeline_events ADD COLUMN payload_sha256 VARCHAR(64)"))
            if "related_user_id" not in columns:
                connection.execute(text("ALTER TABLE timeline_events ADD COLUMN related_user_id INTEGER"))
            rows = connection.execute(
                text(
                    "SELECT id, patient_id, actor_id, payload_json, payload_sha256, related_user_id "
                    "FROM timeline_events WHERE payload_sha256 IS NULL OR related_user_id IS NULL"
                )
            ).all()
            for event_id, patient_id, actor_id, payload_json, stored_digest, stored_related in rows:
                digest = stored_digest or sha256(payload_json.encode("utf-8")).hexdigest()
                related_user_id = stored_related
                if related_user_id is None:
                    try:
                        payload = json.loads(payload_json).get("payload", {})
                    except (TypeError, ValueError):
                        payload = {}
                    related_user_id = payload.get("requestor_id") or payload.get("linked_user_id")
                    if related_user_id is None and str(actor_id) != str(patient_id):
                        try:
                            related_user_id = int(actor_id)
                        except (TypeError, ValueError):
                            related_user_id = None
                connection.execute(
                    text(
                        "UPDATE timeline_events SET payload_sha256 = :digest, "
                        "related_user_id = :related_user_id WHERE id = :event_id"
                    ),
                    {
                        "digest": digest,
                        "related_user_id": related_user_id,
                        "event_id": event_id,
                    },
                )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_timeline_patient_occurred_id "
                    "ON timeline_events(patient_id, occurred_at DESC, id DESC)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_timeline_patient_type_occurred "
                    "ON timeline_events(patient_id, event_type, occurred_at DESC)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_timeline_patient_related_occurred "
                    "ON timeline_events(patient_id, related_user_id, occurred_at DESC)"
                )
            )

        if "outbound_events" in tables:
            columns = {column["name"] for column in inspector.get_columns("outbound_events")}
            if "last_error_code" not in columns:
                connection.execute(text("ALTER TABLE outbound_events ADD COLUMN last_error_code VARCHAR(64)"))
            if "last_error_message" not in columns:
                connection.execute(text("ALTER TABLE outbound_events ADD COLUMN last_error_message VARCHAR(255)"))
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_outbound_patient_status_created "
                    "ON outbound_events(patient_id, status, created_at DESC)"
                )
            )

        if "postoffice_acknowledgements" in tables:
            columns = {
                column["name"] for column in inspector.get_columns("postoffice_acknowledgements")
            }
            if "retry_count" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE postoffice_acknowledgements "
                        "ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "last_attempt_at" not in columns:
                connection.execute(
                    text("ALTER TABLE postoffice_acknowledgements ADD COLUMN last_attempt_at DATETIME")
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
