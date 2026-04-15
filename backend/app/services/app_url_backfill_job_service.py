from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.services.instance_service import AppUrlBackfillProgressSnapshot, AppUrlBackfillResult, InstanceService
from app.services.oci_cli import OCIService


logger = logging.getLogger(__name__)


@dataclass
class AppUrlBackfillJobSnapshot:
    job_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total: int = 0
    processed: int = 0
    updated: int = 0
    skipped_existing: int = 0
    unresolved: int = 0
    failed: int = 0
    current_instance_name: str | None = None
    result: AppUrlBackfillResult | None = None
    error: str | None = None


class AppUrlBackfillJobService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, AppUrlBackfillJobSnapshot] = {}

    def start_job(self) -> AppUrlBackfillJobSnapshot:
        started_at = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())
        snapshot = AppUrlBackfillJobSnapshot(job_id=job_id, status="pending", started_at=started_at)
        with self._lock:
            self._jobs[job_id] = snapshot

        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True, name=f"app-url-backfill-job-{job_id[:8]}")
        thread.start()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> AppUrlBackfillJobSnapshot:
        with self._lock:
            snapshot = self._jobs.get(job_id)
            if snapshot is None:
                raise KeyError(job_id)
            return replace(snapshot)

    def _run_job(self, job_id: str) -> None:
        self._update(job_id, status="running")
        session = SessionLocal()
        try:
            service = InstanceService(session, OCIService())
            result = service.backfill_missing_app_urls(
                progress_callback=lambda progress: self._apply_progress(job_id, progress),
                job_id=job_id,
            )
            self._update(
                job_id,
                status="completed",
                finished_at=datetime.now(timezone.utc),
                current_instance_name=None,
                result=result,
                error=None,
            )
        except Exception as exc:
            logger.exception("app_url_backfill_job_failed [job_id=%s]", job_id)
            self._update(
                job_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                current_instance_name=None,
                error=str(exc),
            )
        finally:
            session.close()

    def _apply_progress(self, job_id: str, progress: AppUrlBackfillProgressSnapshot) -> None:
        self._update(
            job_id,
            total=progress.total,
            processed=progress.processed,
            updated=progress.updated,
            skipped_existing=progress.skipped_existing,
            unresolved=progress.unresolved,
            failed=progress.failed,
            current_instance_name=progress.current_instance_name,
        )

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            snapshot = self._jobs.get(job_id)
            if snapshot is None:
                return
            self._jobs[job_id] = replace(snapshot, **changes)
