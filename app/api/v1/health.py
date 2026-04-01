from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import APIResponse, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse[dict[str, str]])
def health() -> APIResponse[dict[str, str]]:
    return success_response({"status": "ok"})
