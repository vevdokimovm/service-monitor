"""Настройки приложения из переменных окружения и .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация сервера мониторинга."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./monitor.db"
    POLL_TICK_SECONDS: float = 1.0
    CHECK_TIMEOUT_SECONDS: float = 3.0
    HISTORY_LIMIT: int = 200
    API_TOKEN: str = ""  # пусто — API открыт (локально); если задан, нужен заголовок X-API-Token


settings = Settings()
