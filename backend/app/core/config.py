from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from VIRTDECK_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="VIRTDECK_", env_file=".env", extra="ignore")

    libvirt_uri: str = "test:///default"
    database_url: str = "sqlite:///./virtdeck.db"
    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_expire_minutes: int = 30
    log_level: str = "INFO"
    storage_root: str = "/var/lib/libvirt/images"
    console_token_ttl_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
