from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_SALT = "development-only-client-reference-salt"


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
    verification_min_response_seconds: float = Field(default=0.05)

    client_reference_salt: str = Field(default=_DEVELOPMENT_SALT)

    signing_master_key: str | None = Field(default=None)

    session_ttl_hours: int = Field(default=24 * 14)
    auth_rate_limit_per_minute: int = Field(default=10)
    auth_rate_limit_burst: int = Field(default=5)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def production_problems(self) -> list[str]:
        if not self.is_production:
            return []
        problems = []
        if not self.signing_master_key:
            problems.append("SIGNING_MASTER_KEY is not set, so nothing could be signed.")
        if self.client_reference_salt == _DEVELOPMENT_SALT:
            problems.append("CLIENT_REFERENCE_SALT is still the development value.")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
