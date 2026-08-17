from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="WELLNESS_", extra="ignore")

    app_name: str = "Wellness CRUD API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://wellness:wellness@localhost:5432/wellness"
    jwt_secret: SecretStr = SecretStr("development-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "wellness.domain-events.v1"
    sql_echo: bool = False

    @model_validator(mode="after")
    def reject_default_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret.get_secret_value() == "development-only-change-me":
            raise ValueError("WELLNESS_JWT_SECRET must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
