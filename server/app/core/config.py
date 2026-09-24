"""Application settings loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration of the monitoring server."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./monitor.db"
    POLL_TICK_SECONDS: float = 1.0
    CHECK_TIMEOUT_SECONDS: float = 3.0
    HISTORY_LIMIT: int = 200
    API_TOKEN: str = ""  # empty: open API (local use); set it to require the X-API-Token header


settings = Settings()
