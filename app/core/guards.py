from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exception_handlers import (
    ConcurrentRequestBlocked,
    ContentTooLongError,
    DuplicateRequestError,
    RateLimitExceeded,
    SessionNotActiveError,
)

logger = logging.getLogger(__name__)


class ChatGuard:
    """
    问答请求的安全防护层。
    所有检查在 Redis 不可用时自动跳过（fail-open）。
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        self.redis = redis_client
        self.settings = get_settings()

    # ---- 1. 频率限流（滑动窗口） ----

    async def check_rate_limit(self, tenant_code: str, user_id: str) -> None:
        if self.redis is None:
            return

        key = f"rate_limit:chat:{tenant_code}:{user_id}"
        max_rpm = self.settings.guard_max_requests_per_minute

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        current_count = results[0]

        if current_count > max_rpm:
            logger.warning(
                "rate limit exceeded: tenant=%s user=%s count=%d limit=%d",
                tenant_code, user_id, current_count, max_rpm,
            )
            raise RateLimitExceeded()

    # ---- 2. 会话并发锁 ----

    async def acquire_session_lock(self, session_code: str) -> bool:
        if self.redis is None or not self.settings.guard_session_lock_enabled:
            return True

        key = f"chat_lock:{session_code}"
        lock_ttl = int(self.settings.llm_timeout) + 10
        acquired = await self.redis.set(key, "1", nx=True, ex=lock_ttl)

        if not acquired:
            raise ConcurrentRequestBlocked()
        return True

    async def release_session_lock(self, session_code: str) -> None:
        if self.redis is None or not self.settings.guard_session_lock_enabled:
            return
        key = f"chat_lock:{session_code}"
        await self.redis.delete(key)

    # ---- 3. 请求幂等 ----

    async def check_idempotency(self, request_id: str | None) -> None:
        if request_id is None or self.redis is None or not self.settings.guard_idempotency_enabled:
            return

        key = f"idempotent:chat:{request_id}"
        is_new = await self.redis.set(key, "1", nx=True, ex=self.settings.guard_idempotency_ttl)

        if not is_new:
            raise DuplicateRequestError()

    # ---- 4. 消息长度检查 ----

    def check_content_length(self, content: str) -> None:
        max_length = self.settings.guard_max_message_length
        if len(content) > max_length:
            raise ContentTooLongError(max_length)

    # ---- 5. 会话状态检查 ----

    def check_session_active(self, session_status: str) -> None:
        if session_status != "active":
            raise SessionNotActiveError(session_status)
