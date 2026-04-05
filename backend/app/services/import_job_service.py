from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.services.instance_service import ImportAllCompartmentsResult, ImportProgressSnapshot, InstanceService
from app.services.oci_cli import OCIService


logger = logging.getLogger(__name__)


@dataclass
class ImportInstancesJobSnapshot:
    job_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total_compartments: int = 0
    processed_compartments: int = 0
    total_instances: int = 0
    processed_instances: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    current_compartment_name: str | None = None
    current_instance_name: str | None = None
    result: ImportAllCompartmentsResult | None = None
    error: str | None = None


class ImportJobService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, ImportInstancesJobSnapshot] = {}

    def start_import_all_compartments_job(self) -> ImportInstancesJobSnapshot:
        started_at = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())
        snapshot = ImportInstancesJobSnapshot(job_id=job_id, status="pending", started_at=started_at)
        with self._lock:
            self._jobs[job_id] = snapshot

        thread = threading.Thread(target=self._run_import_job, args=(job_id,), daemon=True, name=f"import-job-{job_id[:8]}")
        thread.start()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> ImportInstancesJobSnapshot:
        with self._lock:
            snapshot = self._jobs.get(job_id)
            if snapshot is None:
                raise KeyError(job_id)
            return replace(snapshot)

    def _run_import_job(self, job_id: str) -> None:
        self._update(job_id, status="running")
        session = SessionLocal()
        try:
            service = InstanceService(session, OCIService())
            result = service.import_all_compartment_instances(
                progress_callback=lambda progress: self._apply_progress(job_id, progress),
                job_id=job_id,
            )
            self._update(
                job_id,
                status="completed",
                finished_at=datetime.now(timezone.utc),
                current_compartment_name=None,
                current_instance_name=None,
                result=result,
                error=None,
            )
        except Exception as exc:
            logger.exception("Automatic registration job failed [job_id=%s]", job_id)
            self._update(
                job_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                current_compartment_name=None,
                current_instance_name=None,
                error=str(exc),
            )
        finally:
            session.close()

    def _apply_progress(self, job_id: str, progress: ImportProgressSnapshot) -> None:
        self._update(
            job_id,
            total_compartments=progress.total_compartments,
            processed_compartments=progress.processed_compartments,
            total_instances=progress.total_instances,
            processed_instances=progress.processed_instances,
            created=progress.created,
            updated=progress.updated,
            unchanged=progress.unchanged,
            failed=progress.failed,
            current_compartment_name=progress.current_compartment_name,
            current_instance_name=progress.current_instance_name,
        )

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            snapshot = self._jobs.get(job_id)
            if snapshot is None:
                return
            self._jobs[job_id] = replace(snapshot, **changes)
