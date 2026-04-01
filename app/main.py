from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import configure_logging
from app.core.middleware import RequestLoggingMiddleware, TraceIdMiddleware
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    if settings.app_auto_create_tables:
        init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(api_router)
    register_exception_handlers(app)
    return app


app = create_app()
