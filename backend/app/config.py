from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Parcham OS"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://parcham:parcham@localhost:5432/parcham"
    oidc_issuer: str = "http://localhost:8080/realms/parcham"
    oidc_audience: str = "parcham-api"
    oidc_jwks_url: str = "http://localhost:8080/realms/parcham/protocol/openid-connect/certs"
    nats_url: str = "nats://localhost:4222"
    model_config = SettingsConfigDict(env_prefix="PARCHAM_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
