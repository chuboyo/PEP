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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
