from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "bharosa-backend"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://bharosa_app:bharosa_app@localhost:5432/bharosa"
    )
    migration_database_url: str = Field(
        default="postgresql+psycopg://bharosa_owner:bharosa_owner@localhost:5432/bharosa"
    )
    verification_database_url: str = Field(
        default="postgresql+psycopg://bharosa_verifier:bharosa_verifier@localhost:5432/bharosa"
    )

    log_level: str = Field(default="INFO")

    digital_link_host: str = Field(default="id.bharosa.example")

    verification_rate_limit_per_minute: int = Field(default=30)
    verification_rate_limit_burst: int = Field(default=10)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
