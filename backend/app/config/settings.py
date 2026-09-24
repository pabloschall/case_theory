from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "Game Theory"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = "development-only-change-me-please-32-chars"
    database_url: str = "postgresql+asyncpg://eillen:eillen@localhost:5432/eillen"
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=2, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60)
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_domain: str | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 60
    investigator_case_creation_limit: int = 0
    openai_api_key: str = ""
    ai_text_model: str = "gpt-5-mini"
    ai_image_model: str = "gpt-image-2.5-flare"
    local_storage_path: str = "/app/storage-data"
    storage_provider: Literal["gcs", "fake_gcs"] = "fake_gcs"
    gcs_bucket: str = "eillen-evidence"
    gcs_project_id: str = "eillen-local"
    gcs_signing_service_account: str = ""
    gcs_emulator_internal_url: str = "http://gcs:4443"
    gcs_emulator_public_url: str = "http://localhost:4443"
    evidence_max_upload_bytes: int = 26_214_400
    avatar_max_upload_bytes: int = 8_388_608
    fbi_api_base_url: str = "https://api.fbi.gov/wanted/v1"
    fbi_api_key: str = ""
    fbi_api_timeout: float = 15.0
    fbi_list_cache_seconds: int = 900
    fbi_case_cache_seconds: int = 3600
    fbi_image_max_bytes: int = 8_388_608
    case_invitation_expiry_days: int = 7
    mailgun_base_url: str = ""
    mailgun_api_key: str = ""
    mailgun_from_email: str = ""
    email_verification_expiry_hours: int = 24
    password_reset_expiry_minutes: int = 60
    csrf_cookie_name: str = "eillen_csrf"
    access_cookie_name: str = "eillen_access"
    refresh_cookie_name: str = "eillen_refresh"
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver", "backend"]
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    insecure_markers = ("development-only", "replace-with")
    if settings.environment in {"staging", "production"} and (
        len(settings.secret_key) < 32 or any(marker in settings.secret_key for marker in insecure_markers)
    ):
        raise ValueError("SECRET_KEY must be a non-default secret with at least 32 characters")
    if settings.environment in {"staging", "production"} and not all(
        (settings.mailgun_base_url, settings.mailgun_api_key, settings.mailgun_from_email)
    ):
        raise ValueError("MAILGUN_BASE_URL, MAILGUN_API_KEY, and MAILGUN_FROM_EMAIL are required")
    if settings.environment in {"staging", "production"}:
        if not settings.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true")
        if not settings.frontend_url.startswith("https://"):
            raise ValueError("FRONTEND_URL must use HTTPS")
        if settings.storage_provider != "gcs":
            raise ValueError("STORAGE_PROVIDER must be gcs")
        if not all(
            (settings.gcs_bucket, settings.gcs_project_id, settings.gcs_signing_service_account)
        ):
            raise ValueError(
                "GCS_BUCKET, GCS_PROJECT_ID, and GCS_SIGNING_SERVICE_ACCOUNT are required"
            )
    return settings
