from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeskManagerUserRead(BaseModel):
    id: str
    name: str


class DeskManagerCategoryRead(BaseModel):
    id: str
    name: str


class DeskManagerCreateTicketItem(BaseModel):
    user_id: str
    category_id: str
    description: str = Field(min_length=1, max_length=4000)


class DeskManagerCreateTicketsRequest(BaseModel):
    items: list[DeskManagerCreateTicketItem] = Field(min_length=1)


class DeskManagerCreateTicketResult(BaseModel):
    user_id: str
    category_id: str
    description: str
    status: Literal["success", "failed"]
    message: str
    external_response: Any | None = None


class DeskManagerCreateTicketsResponse(BaseModel):
    total: int
    success_count: int
    failed_count: int
    results: list[DeskManagerCreateTicketResult]
