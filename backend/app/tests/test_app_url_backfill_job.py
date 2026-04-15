from datetime import datetime, timezone

from fastapi import HTTPException

from app.api.routes import create_app_url_backfill_job, get_app_url_backfill_job
from app.core.security import CurrentUser, require_permission
from app.services.app_url_backfill_job_service import AppUrlBackfillJobSnapshot
from app.services.instance_service import AppUrlBackfillItemResult, AppUrlBackfillResult


class FakeBackfillJobService:
    def __init__(self, snapshot: AppUrlBackfillJobSnapshot | None = None) -> None:
        self._snapshot = snapshot

    def start_job(self) -> AppUrlBackfillJobSnapshot:
        assert self._snapshot is not None
        return self._snapshot

    def get_job(self, job_id: str) -> AppUrlBackfillJobSnapshot:
        if self._snapshot is None or self._snapshot.job_id != job_id:
            raise KeyError(job_id)
        return self._snapshot


def test_create_app_url_backfill_job_route_returns_job_header_fields():
    snapshot = AppUrlBackfillJobSnapshot(
        job_id="job-backfill-1",
        status="pending",
        started_at=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
    )
    service = FakeBackfillJobService(snapshot)

    response = create_app_url_backfill_job(CurrentUser("u", None, [], ["instances.manage"], "local", False, None), service)

    assert response.job_id == "job-backfill-1"
    assert response.status == "pending"


def test_get_app_url_backfill_job_route_serializes_result():
    result = AppUrlBackfillResult(
        total=3,
        processed=3,
        updated=1,
        skipped_existing=1,
        unresolved=1,
        failed=0,
        items=[
            AppUrlBackfillItemResult(
                instance_id="instance-1",
                ocid="ocid1.instance.oc1..abc",
                name="OCIXDOC-HMG-CLIENTE-A",
                derived_app_url="cliente-ahmg.docnix.com.br",
                outcome="updated",
                message=None,
            )
        ],
    )
    snapshot = AppUrlBackfillJobSnapshot(
        job_id="job-backfill-2",
        status="completed",
        started_at=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 14, 12, 1, tzinfo=timezone.utc),
        total=3,
        processed=3,
        updated=1,
        skipped_existing=1,
        unresolved=1,
        failed=0,
        current_instance_name=None,
        result=result,
        error=None,
    )
    service = FakeBackfillJobService(snapshot)

    response = get_app_url_backfill_job(
        "job-backfill-2",
        CurrentUser("u", None, [], ["instances.manage"], "local", False, None),
        service,
    )

    assert response.status == "completed"
    assert response.result is not None
    assert response.result.updated == 1
    assert response.result.items[0].outcome == "updated"


def test_get_app_url_backfill_job_route_returns_404_when_missing():
    service = FakeBackfillJobService(None)

    try:
        get_app_url_backfill_job(
            "missing-job",
            CurrentUser("u", None, [], ["instances.manage"], "local", False, None),
            service,
        )
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing backfill job to raise HTTPException")


def test_instances_manage_permission_blocks_unauthorized_user():
    dependency = require_permission("instances.manage")

    try:
        dependency(CurrentUser("u", None, [], ["instances.view"], "local", False, None))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected unauthorized user to be blocked")
