from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None
    trace_id: str | None = None


def success_response(data: T) -> APIResponse[T]:
    return APIResponse[T](data=data)
