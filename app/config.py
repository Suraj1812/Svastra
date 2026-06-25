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
    app_version = os.getenv("APP_VERSION", "1.1.0")
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
    terminology_bundle_entry_terms_path = _path_from_env(
        "SVASTRA_TERMINOLOGY_ENTRY_TERMS_PATH",
        BASE_DIR / "svp_terminology_sqlitedb" / "svp_entry_terms.json",
    )
    session_ttl_hours = int(os.getenv("SESSION_TTL_HOURS", "24"))
    otp_ttl_seconds = int(os.getenv("OTP_TTL_SECONDS", "300"))
    otp_resend_cooldown_seconds = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "30"))
    otp_max_attempts = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    mock_otp = os.getenv("MOCK_OTP", "123456")
    postoffice_max_retries = int(os.getenv("POSTOFFICE_MAX_RETRIES", "5"))
    monitor_max_page_size = int(os.getenv("MONITOR_MAX_PAGE_SIZE", "100"))
    monitor_max_window_days = int(os.getenv("MONITOR_MAX_WINDOW_DAYS", "366"))
    monitor_cursor_secret = os.getenv(
        "MONITOR_CURSOR_SECRET",
        "local-development-only-change-before-production",
    )
    max_request_bytes = int(os.getenv("MAX_REQUEST_BYTES", str(1024 * 1024)))
    attachment_max_bytes = int(os.getenv("ATTACHMENT_MAX_BYTES", str(5 * 1024 * 1024)))
    attachment_storage_path = _path_from_env(
        "ATTACHMENT_STORAGE_PATH",
        BASE_DIR / "data" / "private_attachments",
    )
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    def validate(self):
        ranges = {
            "SESSION_TTL_HOURS": (self.session_ttl_hours, 1, 168),
            "OTP_TTL_SECONDS": (self.otp_ttl_seconds, 60, 900),
            "OTP_RESEND_COOLDOWN_SECONDS": (self.otp_resend_cooldown_seconds, 1, 300),
            "OTP_MAX_ATTEMPTS": (self.otp_max_attempts, 1, 10),
            "POSTOFFICE_MAX_RETRIES": (self.postoffice_max_retries, 1, 20),
            "MONITOR_MAX_PAGE_SIZE": (self.monitor_max_page_size, 1, 100),
            "MONITOR_MAX_WINDOW_DAYS": (self.monitor_max_window_days, 1, 3660),
            "MAX_REQUEST_BYTES": (self.max_request_bytes, 64 * 1024, 10 * 1024 * 1024),
            "ATTACHMENT_MAX_BYTES": (
                self.attachment_max_bytes,
                64 * 1024,
                20 * 1024 * 1024,
            ),
        }
        for name, (value, minimum, maximum) in ranges.items():
            if not minimum <= value <= maximum:
                raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
        if len(self.monitor_cursor_secret) < 32:
            raise RuntimeError("MONITOR_CURSOR_SECRET must contain at least 32 characters")
        if not self.cors_origins or "*" in self.cors_origins:
            raise RuntimeError("CORS_ORIGINS must contain explicit trusted origins")
        return self


settings = Settings().validate()
