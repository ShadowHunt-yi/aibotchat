from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    channel: str = Field(min_length=1, max_length=64)
    external_user_id: str = Field(min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None


class SessionCreateResponse(BaseModel):
    session_code: str
    status: str
    created_at: datetime
