from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import configure_logging
from app.core.middleware import RequestLoggingMiddleware, TraceIdMiddleware
from app.db.session import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    if settings.app_auto_create_tables:
        init_db()

    # 初始化 Redis 异步连接
    redis_client = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.resolved_redis_url, decode_responses=True,
        )
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected: %s", settings.resolved_redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable, guards will be disabled: %s", exc)
        app.state.redis = None

    yield

    # 关闭 Redis
    if redis_client is not None:
        await redis_client.aclose()


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
