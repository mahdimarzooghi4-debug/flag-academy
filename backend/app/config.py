from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Parcham OS"
    app_env: str = "development"
    database_url: str = Field()
    oidc_issuer: str = "http://localhost:8080/realms/parcham"
    oidc_audience: str = "parcham-api"
    oidc_jwks_url: str = "http://localhost:8080/realms/parcham/protocol/openid-connect/certs"
    nats_url: str = "nats://localhost:4222"
    cors_origins: str = "http://localhost:5173"
    otel_exporter_otlp_endpoint: str | None = None
    model_config = SettingsConfigDict(env_prefix="PARCHAM_", env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
