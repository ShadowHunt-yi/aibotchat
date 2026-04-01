from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.messages import router as messages_router
from app.api.v1.sessions import router as sessions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(messages_router)
