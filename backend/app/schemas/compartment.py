from datetime import datetime

from app.schemas.common import AppBaseModel


class CompartmentRead(AppBaseModel):
    id: str
    name: str
    ocid: str
    active: bool
    created_at: datetime
    updated_at: datetime
