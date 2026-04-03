from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HistoryMessage(BaseModel):
    message_code: str
    role: str
    content: str | None
    status: str
    created_at: datetime


class HistoryResponse(BaseModel):
    session_code: str
    items: list[HistoryMessage]
    total: int
