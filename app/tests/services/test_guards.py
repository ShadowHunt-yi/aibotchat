from __future__ import annotations

from asyncio import Runner

import pytest

from app.core.exception_handlers import (
    ContentTooLongError,
    SessionNotActiveError,
)
from app.core.guards import ChatGuard


def test_check_content_length_ok():
    guard = ChatGuard(redis_client=None)
    # Should not raise
    guard.check_content_length("短消息")


def test_check_content_length_too_long():
    guard = ChatGuard(redis_client=None)
    with pytest.raises(ContentTooLongError):
        guard.check_content_length("x" * 5000)


def test_check_session_active_ok():
    guard = ChatGuard(redis_client=None)
    # Should not raise
    guard.check_session_active("active")


def test_check_session_active_closed():
    guard = ChatGuard(redis_client=None)
    with pytest.raises(SessionNotActiveError):
        guard.check_session_active("closed")


def test_check_session_active_expired():
    guard = ChatGuard(redis_client=None)
    with pytest.raises(SessionNotActiveError):
        guard.check_session_active("expired")


def test_rate_limit_skipped_without_redis():
    guard = ChatGuard(redis_client=None)
    with Runner() as runner:
        runner.run(guard.check_rate_limit("demo_tenant", "user_1"))


def test_idempotency_skipped_without_redis():
    guard = ChatGuard(redis_client=None)
    with Runner() as runner:
        runner.run(guard.check_idempotency("req_001"))


def test_session_lock_skipped_without_redis():
    guard = ChatGuard(redis_client=None)

    async def _test():
        result = await guard.acquire_session_lock("s_001")
        assert result is True
        await guard.release_session_lock("s_001")

    with Runner() as runner:
        runner.run(_test())
