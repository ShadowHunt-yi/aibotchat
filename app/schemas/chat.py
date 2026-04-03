from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessagePayload(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    session_code: str = Field(min_length=1, max_length=64)
    message: ChatMessagePayload
    stream: bool = False
    model: str | None = None
    request_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    message_code: str
    role: str
    content: str
    finish_reason: str
