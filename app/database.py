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
    from app.models import allergy, audit, care, consent, postoffice, rbac, relationship, session, terminology, user, workflow  # noqa: F401
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
            if "diagnosis_concept_id" not in columns:
                connection.execute(
                    text("ALTER TABLE care_plans ADD COLUMN diagnosis_concept_id VARCHAR(64)")
                )
            if "diagnosis_term" not in columns:
                connection.execute(
                    text("ALTER TABLE care_plans ADD COLUMN diagnosis_term VARCHAR(160)")
                )
            if "diagnosis_notes" not in columns:
                connection.execute(text("ALTER TABLE care_plans ADD COLUMN diagnosis_notes TEXT"))

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
            if "provider_id" not in columns:
                connection.execute(text("ALTER TABLE timeline_events ADD COLUMN provider_id INTEGER"))
            if "episode_id" not in columns:
                connection.execute(text("ALTER TABLE timeline_events ADD COLUMN episode_id VARCHAR(100)"))
            if "encounter_id" not in columns:
                connection.execute(text("ALTER TABLE timeline_events ADD COLUMN encounter_id VARCHAR(100)"))
            rows = connection.execute(
                text(
                    "SELECT id, patient_id, actor_id, payload_json, payload_sha256, related_user_id, "
                    "provider_id, episode_id, encounter_id "
                    "FROM timeline_events WHERE payload_sha256 IS NULL OR related_user_id IS NULL "
                    "OR provider_id IS NULL OR episode_id IS NULL OR encounter_id IS NULL"
                )
            ).all()
            for (
                event_id,
                patient_id,
                actor_id,
                payload_json,
                stored_digest,
                stored_related,
                stored_provider_id,
                stored_episode_id,
                stored_encounter_id,
            ) in rows:
                digest = stored_digest or sha256(payload_json.encode("utf-8")).hexdigest()
                related_user_id = stored_related
                provider_id = stored_provider_id
                episode_id = stored_episode_id
                encounter_id = stored_encounter_id
                try:
                    document = json.loads(payload_json)
                    payload = document.get("payload") or document.get("body") or {}
                except (TypeError, ValueError):
                    payload = {}
                if related_user_id is None:
                    related_user_id = payload.get("requestor_id") or payload.get("linked_user_id")
                    if related_user_id is None and str(actor_id) != str(patient_id):
                        try:
                            related_user_id = int(actor_id)
                        except (TypeError, ValueError):
                            related_user_id = None
                if provider_id is None:
                    provider_id = payload.get("provider_id")
                if episode_id is None:
                    care_plan_id = payload.get("care_plan_id")
                    advisory_id = payload.get("advisory_id")
                    episode_id = (
                        f"care_plan:{care_plan_id}"
                        if care_plan_id
                        else f"advisory:{advisory_id}" if advisory_id else None
                    )
                if encounter_id is None:
                    task_id = payload.get("task_id")
                    alert_id = payload.get("alert_id")
                    encounter_id = (
                        f"task:{task_id}"
                        if task_id
                        else f"alert:{alert_id}" if alert_id else None
                    )
                connection.execute(
                    text(
                        "UPDATE timeline_events SET payload_sha256 = :digest, "
                        "related_user_id = :related_user_id, provider_id = :provider_id, "
                        "episode_id = :episode_id, encounter_id = :encounter_id "
                        "WHERE id = :event_id"
                    ),
                    {
                        "digest": digest,
                        "related_user_id": related_user_id,
                        "provider_id": provider_id,
                        "episode_id": episode_id,
                        "encounter_id": encounter_id,
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
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_timeline_patient_provider_occurred "
                    "ON timeline_events(patient_id, provider_id, occurred_at DESC)"
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

        if "clinical_alerts" in tables:
            columns = {column["name"] for column in inspector.get_columns("clinical_alerts")}
            if "notification_mode" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE clinical_alerts ADD COLUMN notification_mode "
                        "VARCHAR(32) NOT NULL DEFAULT 'immediate'"
                    )
                )
            if "resolved_at" not in columns:
                connection.execute(text("ALTER TABLE clinical_alerts ADD COLUMN resolved_at DATETIME"))
            if "updated_at" not in columns:
                connection.execute(text("ALTER TABLE clinical_alerts ADD COLUMN updated_at DATETIME"))
            table_sql = connection.execute(
                text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'clinical_alerts'")
            ).scalar() or ""
            if "RESOLVED" not in table_sql or "'OPEN'" in table_sql:
                connection.execute(text("DROP TABLE IF EXISTS clinical_alerts_rebuilt"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE clinical_alerts_rebuilt (
                            id INTEGER NOT NULL,
                            alert_uid VARCHAR(64) NOT NULL,
                            advisory_id INTEGER NOT NULL,
                            task_id INTEGER,
                            provider_id INTEGER NOT NULL,
                            patient_id INTEGER NOT NULL,
                            alert_type VARCHAR(32) NOT NULL,
                            severity VARCHAR(20) NOT NULL,
                            message VARCHAR(500) NOT NULL,
                            notification_mode VARCHAR(32) NOT NULL DEFAULT 'immediate',
                            status VARCHAR(20) NOT NULL DEFAULT 'NEW',
                            event_id VARCHAR(64),
                            acknowledged_at DATETIME,
                            resolved_at DATETIME,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (id),
                            CONSTRAINT ck_clinical_alerts_type
                                CHECK (alert_type in ('allergy_conflict', 'non_response', 'value_threshold')),
                            CONSTRAINT ck_clinical_alerts_severity
                                CHECK (severity in ('low', 'medium', 'high', 'critical')),
                            CONSTRAINT ck_clinical_alerts_status
                                CHECK (status in ('NEW', 'ACKNOWLEDGED', 'RESOLVED')),
                            CONSTRAINT ck_clinical_alerts_notification_mode
                                CHECK (notification_mode in ('immediate', 'daily_summary', 'both')),
                            FOREIGN KEY(advisory_id) REFERENCES advisories (id),
                            FOREIGN KEY(task_id) REFERENCES care_tasks (id),
                            FOREIGN KEY(provider_id) REFERENCES users (id),
                            FOREIGN KEY(patient_id) REFERENCES users (id)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO clinical_alerts_rebuilt (
                            id, alert_uid, advisory_id, task_id, provider_id, patient_id,
                            alert_type, severity, message, notification_mode, status,
                            event_id, acknowledged_at, resolved_at, created_at, updated_at
                        )
                        SELECT
                            id,
                            alert_uid,
                            advisory_id,
                            task_id,
                            provider_id,
                            patient_id,
                            alert_type,
                            severity,
                            message,
                            notification_mode,
                            CASE status WHEN 'OPEN' THEN 'NEW' ELSE status END,
                            event_id,
                            acknowledged_at,
                            resolved_at,
                            created_at,
                            COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                        FROM clinical_alerts
                        """
                    )
                )
                connection.execute(text("DROP TABLE clinical_alerts"))
                connection.execute(
                    text("ALTER TABLE clinical_alerts_rebuilt RENAME TO clinical_alerts")
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_clinical_alerts_alert_uid "
                        "ON clinical_alerts(alert_uid)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_advisory_id "
                        "ON clinical_alerts(advisory_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_task_id "
                        "ON clinical_alerts(task_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_provider_id "
                        "ON clinical_alerts(provider_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_patient_id "
                        "ON clinical_alerts(patient_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_alert_type "
                        "ON clinical_alerts(alert_type)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_clinical_alerts_status "
                        "ON clinical_alerts(status)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_clinical_alerts_event_id "
                        "ON clinical_alerts(event_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_clinical_alerts_provider_status_created "
                        "ON clinical_alerts(provider_id, status, created_at DESC)"
                    )
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
