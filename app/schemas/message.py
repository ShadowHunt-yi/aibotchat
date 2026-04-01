from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class MessagePayload(BaseModel):
    type: Literal["text", "event", "tool_result"] = "text"
    content: str | None = None
    content_json: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "MessagePayload":
        if self.type == "text" and not self.content:
            raise ValueError("content is required for text message")
        if not self.content and not self.content_json:
            raise ValueError("content or content_json is required")
        return self


class MessageCreateRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    session_code: str = Field(min_length=1, max_length=64)
    message: MessagePayload
    request_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] | None = None


class MessageCreateResponse(BaseModel):
    message_code: str
    role: str
    status: str
