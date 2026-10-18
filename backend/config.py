import os
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq connection options we pass through. Anything else in a provider URL is dropped,
# e.g. the "supa=..." pooler parameter that Supabase/Vercel integrations append and libpq rejects.
_LIBPQ_PARAMS = {"sslmode", "sslrootcert", "connect_timeout", "application_name", "options",
                 "channel_binding", "target_session_attrs"}


def normalise_database_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k in _LIBPQ_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    """Configuration comes only from environment variables (or a local .env for development)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Hosted PostgreSQL. Vercel's Neon/Supabase integrations set DATABASE_URL and/or POSTGRES_URL.
    database_url: str = Field("", validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL",
                                                                "POSTGRES_URL_NON_POOLING"))
    environment: str = "development"
    force_demo: bool = Field(False, validation_alias="DEMO_MODE")  # DEMO_MODE=true forces demo even if a DB is set
    admin_api_key: str = ""  # required for any endpoint that changes data (simulator, incident resolve)
    cors_origins: str = ""  # same-origin deployment needs none; only for a separately hosted frontend
    cors_origin_regex: str = ""

    sim_device_count: int = 24
    sim_seed: int = 42
    retention_hours: int = 72
    active_window_minutes: int = 60

    @field_validator("database_url")
    @classmethod
    def _normalise(cls, v: str) -> str:
        return normalise_database_url(v)

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_database(self) -> bool:
        return bool(self.database_url) and not self.force_demo

    @property
    def is_production(self) -> bool:
        """True on Vercel production/preview deployments or when ENVIRONMENT=production."""
        return self.environment.lower() == "production" or os.getenv("VERCEL_ENV") in ("production", "preview")


@lru_cache
def get_settings() -> Settings:
    return Settings()
