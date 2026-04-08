from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit_middleware import AuditAccessMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.services.scheduler import SchedulerRunner


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = SchedulerRunner(settings.scheduler_poll_seconds)
        await scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()


app = FastAPI(title="OCI Automation API", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditAccessMiddleware)
app.include_router(router)
