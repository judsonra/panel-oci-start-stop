from datetime import datetime

from app.models.execution_log import ExecutionSource, ExecutionStatus
from app.schemas.common import AppBaseModel


class ExecutionLogRead(AppBaseModel):
    id: str
    instance_id: str
    instance_name: str | None = None
    instance_state: str | None = None
    action: str
    source: ExecutionSource
    status: ExecutionStatus
    stdout_summary: str | None
    stderr_summary: str | None
    started_at: datetime
    finished_at: datetime | None
