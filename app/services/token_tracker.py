from __future__ import annotations

import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TokenTracker:
    """
    追踪 LLM token 用量。
    按 tenant 维度按天累计，数据存入 Redis，保留 7 天。
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        self.redis = redis_client

    async def record_usage(
        self,
        tenant_code: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict:
        total = prompt_tokens + completion_tokens
        today = datetime.now(UTC).strftime("%Y%m%d")

        if self.redis is None:
            return {"today_total": total}

        prefix = f"token_usage:{tenant_code}:{today}"
        keys = [f"{prefix}:total", f"{prefix}:prompt", f"{prefix}:completion", f"{prefix}:calls"]

        pipe = self.redis.pipeline()
        pipe.incrby(keys[0], total)
        pipe.incrby(keys[1], prompt_tokens)
        pipe.incrby(keys[2], completion_tokens)
        pipe.incr(keys[3])
        for k in keys:
            pipe.expire(k, 7 * 86400)
        results = await pipe.execute()

        today_total = results[0]
        logger.info(
            "token usage: tenant=%s model=%s prompt=%d completion=%d total=%d today_cumulative=%d",
            tenant_code, model, prompt_tokens, completion_tokens, total, today_total,
        )
        return {"today_total": today_total}

    async def get_daily_usage(self, tenant_code: str, date: str | None = None) -> dict:
        if self.redis is None:
            return {"total": 0, "prompt": 0, "completion": 0, "calls": 0}

        day = date or datetime.now(UTC).strftime("%Y%m%d")
        prefix = f"token_usage:{tenant_code}:{day}"

        pipe = self.redis.pipeline()
        pipe.get(f"{prefix}:total")
        pipe.get(f"{prefix}:prompt")
        pipe.get(f"{prefix}:completion")
        pipe.get(f"{prefix}:calls")
        results = await pipe.execute()

        return {
            "total": int(results[0] or 0),
            "prompt": int(results[1] or 0),
            "completion": int(results[2] or 0),
            "calls": int(results[3] or 0),
        }
