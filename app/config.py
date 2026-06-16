import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _path_from_env(name: str, default: Path):
    value = Path(os.getenv(name, default))
    if value.is_absolute():
        return value
    return BASE_DIR / value


class Settings:
    app_name = os.getenv("APP_NAME", "SVASTRA+ Authentication MVP")
    app_version = os.getenv("APP_VERSION", "1.0.0")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./svastra_auth_mvp.db")
    consent_version = os.getenv("CONSENT_VERSION", "v1")
    consent_document_path = _path_from_env(
        "CONSENT_DOCUMENT_PATH",
        BASE_DIR / "data" / "svp_unified_consent.md",
    )
    reference_terms_path = _path_from_env(
        "REFERENCE_TERMS_PATH",
        BASE_DIR / "data" / "svp_entry_terms.json",
    )
    session_ttl_hours = int(os.getenv("SESSION_TTL_HOURS", "24"))
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
