from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str  # required, no default: never hard-code credentials
    environment: str = "development"
    cors_origins: str = ""  # comma-separated exact origins
    cors_origin_regex: str = ""  # optional, e.g. https://twin-.*\.vercel\.app
    admin_api_key: str = ""  # protects simulator/mutating endpoints

    sim_device_count: int = 24
    sim_seed: int = 42
    sim_tick_seconds: float = 5.0
    sim_autostart: bool = False
    auto_seed: bool = False  # seed automatically on startup if DB is empty
    retention_hours: int = 72

    model_dir: str = "model_store"
    active_window_minutes: int = 60

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
