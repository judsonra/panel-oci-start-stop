import asyncio
import contextlib
import logging

from app.db.session import SessionLocal
from app.services.instance_service import InstanceService
from app.services.oci_cli import OCIService
from app.services.schedule_service import ScheduleService


logger = logging.getLogger(__name__)


class SchedulerRunner:
    def __init__(self, poll_seconds: int) -> None:
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def _loop(self) -> None:
        while True:
            try:
                with SessionLocal() as session:
                    oci_service = OCIService()
                    instance_service = InstanceService(session, oci_service)
                    schedule_service = ScheduleService(session, instance_service)
                    triggered = schedule_service.process_due_schedules()
                    if triggered:
                        logger.info("Triggered %s schedules", triggered)
            except Exception:
                logger.exception("Scheduler cycle failed")
            await asyncio.sleep(self.poll_seconds)

