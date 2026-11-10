from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://pep:pep@localhost:5432/pep"
    test_database_url: str = "postgresql+psycopg://pep:pep@localhost:5432/pep_test"
    jwt_secret: str = "dev-only-change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cors_origins: str = "http://localhost:5173"
    app_public_url: str = "http://localhost:5173"
    superadmin_email: str = "superadmin@example.com"
    superadmin_password: str = "changeme-superadmin"
    # Off by default: use `python -m scripts.create_superadmin` (esp. prod).
    # Set true only for local convenience.
    seed_superadmin_on_startup: bool = False

    # WhatsApp Cloud API (optional; empty → in-memory adapter for local/CI).
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_template_start: str = "pep_survey_start"
    whatsapp_template_reminder: str = "pep_survey_reminder"

    # Cron / internal jobs (empty → internal routes reject).
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
