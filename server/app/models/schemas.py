"""Схемы Pydantic: отдельные модели для входа и выхода."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TargetCreate(BaseModel):
    """Данные для добавления нового сервиса."""

    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    interval_seconds: int = Field(default=10, ge=2, le=3600)
    expected_status: int = Field(default=200, ge=100, le=599)


class TargetOut(BaseModel):
    """Сервис в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    created_at: datetime


class CheckOut(BaseModel):
    """Результат одной проверки."""

    model_config = ConfigDict(from_attributes=True)

    checked_at: datetime
    is_up: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None


class TargetStatus(BaseModel):
    """Сводное состояние сервиса для таблицы в клиенте."""

    id: int
    name: str
    url: str
    state: str
    last_checked_at: datetime | None
    last_latency_ms: float | None
    uptime_percent: float | None
    checks_total: int


class AuditOut(BaseModel):
    """Запись журнала действий."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    client_ip: str
    action: str
    details: str
