"""Business logic: target management, probing and status aggregation."""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.exceptions import DuplicateTargetError, TargetNotFoundError
from app.models.orm import CheckResult, Target
from app.models.schemas import CheckOut, TargetCreate, TargetStatus
from app.repositories.monitor_repository import MonitorRepository

logger = logging.getLogger(__name__)


class MonitorService:
    """Operations requested by clients through the API."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = MonitorRepository(session)

    async def create_target(self, data: TargetCreate, client_ip: str) -> Target:
        """Register a target; names are unique."""
        if await self.repo.get_target_by_name(data.name):
            raise DuplicateTargetError(data.name)
        target = await self.repo.add_target(Target(
            name=data.name, url=str(data.url),
            interval_seconds=data.interval_seconds, expected_status=data.expected_status))
        await self.repo.log(client_ip, "target_created", f"{target.name} {target.url}")
        return target

    async def delete_target(self, target_id: int, client_ip: str) -> None:
        """Remove a target together with its history."""
        target = await self._get(target_id)
        await self.repo.delete_target(target)
        await self.repo.log(client_ip, "target_deleted", target.name)

    async def list_targets(self) -> list[Target]:
        return await self.repo.list_targets()

    async def status(self) -> list[TargetStatus]:
        """Dashboard view: last state, latency and uptime of every target."""
        out = []
        for target in await self.repo.list_targets():
            last = await self.repo.history(target.id, 1)
            total, up = await self.repo.uptime(target.id)
            state = "PENDING" if not last else ("UP" if last[0].is_up else "DOWN")
            out.append(TargetStatus(
                id=target.id, name=target.name, url=target.url, state=state,
                last_checked_at=last[0].checked_at if last else None,
                last_latency_ms=last[0].latency_ms if last else None,
                uptime_percent=round(100 * up / total, 1) if total else None,
                checks_total=total))
        return out

    async def history(self, target_id: int, limit: int) -> list[CheckOut]:
        await self._get(target_id)
        rows = await self.repo.history(target_id, min(limit, settings.HISTORY_LIMIT))
        return [CheckOut.model_validate(r) for r in rows]

    async def _get(self, target_id: int) -> Target:
        target = await self.repo.get_target(target_id)
        if target is None:
            raise TargetNotFoundError(target_id)
        return target


class Prober:
    """Performs one HTTP check of a target."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def probe(self, target: Target) -> CheckResult:
        started = time.perf_counter()
        try:
            response = await self.client.get(target.url, timeout=settings.CHECK_TIMEOUT_SECONDS)
            latency = (time.perf_counter() - started) * 1000
            is_up = response.status_code == target.expected_status
            return CheckResult(target_id=target.id, is_up=is_up, status_code=response.status_code,
                               latency_ms=round(latency, 1),
                               error=None if is_up else f"expected {target.expected_status}")
        except httpx.HTTPError as exc:
            return CheckResult(target_id=target.id, is_up=False, status_code=None, latency_ms=None,
                               error=type(exc).__name__)


class Scheduler:
    """Background loop: every tick probes the targets whose interval has elapsed."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="monitor-scheduler")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def tick(self, prober: Prober) -> int:
        """Probe all due targets once; return how many were checked."""
        async with self.session_factory() as session:
            repo = MonitorRepository(session)
            targets = await repo.list_targets()
            last = await repo.last_check_times()
        now = datetime.now(timezone.utc)
        due = [t for t in targets if t.id not in last
               or now - _aware(last[t.id]) >= timedelta(seconds=t.interval_seconds)]
        results = await asyncio.gather(*(prober.probe(t) for t in due))
        async with self.session_factory() as session:
            repo = MonitorRepository(session)
            for result in results:
                await repo.add_check(result)
        return len(due)

    async def _run(self) -> None:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            prober = Prober(client)
            while True:
                try:
                    await self.tick(prober)
                except Exception:  # the loop must survive a DB hiccup; the error is logged
                    logger.exception("scheduler tick failed")
                await asyncio.sleep(settings.POLL_TICK_SECONDS)


def _aware(moment: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
