"""Application settings.

Everything is environment driven so the same image can run locally, in Docker
and on a hosting platform without code changes.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Customer Learning Hub API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # SQLite by default; any SQLAlchemy URL (e.g. postgresql+psycopg://...) works.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'clh.db').as_posix()}"

    # Comma separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://localhost:8080"

    # Demo-only. The prototype has no real authentication; see docs/AUTH.md.
    demo_mode: bool = True
    seed_on_startup: bool = True
    seed_demo_data: bool = True

    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
