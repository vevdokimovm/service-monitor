"""HTTP layer: parse request, call the service, return a schema."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.schemas import AuditOut, CheckOut, TargetCreate, TargetOut, TargetStatus
from app.repositories.monitor_repository import MonitorRepository
from app.services.monitor_service import MonitorService

router = APIRouter(prefix="/api")


def service(session: AsyncSession = Depends(get_session)) -> MonitorService:
    return MonitorService(session)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/targets", response_model=list[TargetOut])
async def list_targets(svc: MonitorService = Depends(service)):
    return await svc.list_targets()


@router.post("/targets", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
async def create_target(data: TargetCreate, request: Request, svc: MonitorService = Depends(service)):
    return await svc.create_target(data, client_ip(request))


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(target_id: int, request: Request, svc: MonitorService = Depends(service)):
    await svc.delete_target(target_id, client_ip(request))


@router.get("/status", response_model=list[TargetStatus])
async def get_status(svc: MonitorService = Depends(service)):
    return await svc.status()


@router.get("/targets/{target_id}/history", response_model=list[CheckOut])
async def history(target_id: int, limit: int = 20, svc: MonitorService = Depends(service)):
    return await svc.history(target_id, limit)


@router.get("/audit", response_model=list[AuditOut])
async def audit(limit: int = 50, session: AsyncSession = Depends(get_session)):
    return await MonitorRepository(session).audit(limit)
