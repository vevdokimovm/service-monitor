"""FastAPI application: routes, exception mapping and the background scheduler."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.database import SessionLocal, init_db
from app.core.exceptions import DuplicateTargetError, TargetNotFoundError
from app.services.monitor_service import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler = Scheduler(SessionLocal)
    if app.state.run_scheduler:
        scheduler.start()
    yield
    await scheduler.stop()


def create_app(run_scheduler: bool = True) -> FastAPI:
    """Application factory; tests switch the background loop off."""
    app = FastAPI(title="Service Monitor", version="1.0.0", lifespan=lifespan)
    app.state.run_scheduler = run_scheduler
    app.include_router(router)

    @app.exception_handler(TargetNotFoundError)
    async def not_found(_: Request, exc: TargetNotFoundError):
        return JSONResponse(status_code=404, content={"detail": f"target {exc} not found"})

    @app.exception_handler(DuplicateTargetError)
    async def duplicate(_: Request, exc: DuplicateTargetError):
        return JSONResponse(status_code=409, content={"detail": f"target '{exc}' already exists"})

    return app


app = create_app()
