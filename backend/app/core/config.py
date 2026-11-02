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

    # Production: real authentication, empty database on startup.
    demo_mode: bool = False
    seed_on_startup: bool = False
    seed_demo_data: bool = False

    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    # Set true only when served over HTTPS; Docker's local stack is HTTP.
    cookie_secure: bool = False

    # Failed sign-ins allowed per window before the caller is throttled. Set to 0
    # to disable the limiter (not recommended outside a throwaway demo).
    login_max_failures: int = 8
    login_window_seconds: int = 300
    # Trust X-Forwarded-For for the client address. Enable only behind a proxy
    # that overwrites the header; otherwise a caller can spoof it.
    trust_proxy_headers: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
