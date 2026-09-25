"""Доступ к данным: сервисы, проверки и журнал. Бизнес-логики здесь нет."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import AuditLog, CheckResult, Target


class MonitorRepository:
    """Запросы к таблицам мониторинга."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_targets(self) -> list[Target]:
        result = await self.session.execute(select(Target).order_by(Target.id))
        return list(result.scalars())

    async def get_target(self, target_id: int) -> Target | None:
        return await self.session.get(Target, target_id)

    async def get_target_by_name(self, name: str) -> Target | None:
        result = await self.session.execute(select(Target).where(Target.name == name))
        return result.scalar_one_or_none()

    async def add_target(self, target: Target) -> Target:
        self.session.add(target)
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def delete_target(self, target: Target) -> None:
        await self.session.execute(delete(CheckResult).where(CheckResult.target_id == target.id))
        await self.session.delete(target)
        await self.session.commit()

    async def add_check(self, check: CheckResult) -> None:
        self.session.add(check)
        await self.session.commit()

    async def last_check_times(self) -> dict[int, datetime]:
        result = await self.session.execute(
            select(CheckResult.target_id, func.max(CheckResult.checked_at)).group_by(CheckResult.target_id))
        return dict(result.all())

    async def history(self, target_id: int, limit: int) -> list[CheckResult]:
        result = await self.session.execute(
            select(CheckResult).where(CheckResult.target_id == target_id)
            .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc()).limit(limit))
        return list(result.scalars())

    async def uptime(self, target_id: int) -> tuple[int, int]:
        """Возвращает (всего проверок, успешных) для сервиса."""
        result = await self.session.execute(
            select(func.count(CheckResult.id), func.count(CheckResult.id).filter(CheckResult.is_up))
            .where(CheckResult.target_id == target_id))
        total, up = result.one()
        return int(total), int(up)

    async def log(self, client_ip: str, action: str, details: str = "") -> None:
        self.session.add(AuditLog(client_ip=client_ip, action=action, details=details[:500]))
        await self.session.commit()

    async def audit(self, limit: int) -> list[AuditLog]:
        result = await self.session.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))
        return list(result.scalars())
