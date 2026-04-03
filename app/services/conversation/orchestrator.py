from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exception_handlers import NotFoundError
from app.core.guards import ChatGuard
from app.db.models.message import Message
from app.db.models.session import ChatSession
from app.db.models.tenant import Tenant
from app.db.repositories.event_repo import EventRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.session_repo import SessionRepository
from app.services.conversation.context_manager import ContextManager
from app.services.conversation.prompt_builder import PromptBuilder
from app.services.llm import get_llm_provider
from app.services.llm.base import ChatRequest
from app.services.token_tracker import TokenTracker
from app.utils.ids import generate_message_code
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    def __init__(self, db: Session, redis_client: Redis | None = None) -> None:
        self.db = db
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.event_repo = EventRepository(db)

        self.settings = get_settings()
        self.context_mgr = ContextManager(db, max_rounds=self.settings.llm_max_context_rounds)
        self.prompt_builder = PromptBuilder()
        self.llm = get_llm_provider()
        self.guard = ChatGuard(redis_client)
        self.token_tracker = TokenTracker(redis_client)

    # ---------- 内部：校验 + 保存用户消息 ----------

    def _validate_and_save_user_message(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
    ) -> tuple[Tenant, ChatSession, Message]:
        """校验 tenant/session，保存用户消息，返回 (tenant, session, user_message)"""
        tenant = self.session_repo.get_tenant_by_code(tenant_code)
        if tenant is None:
            raise NotFoundError("tenant not found")

        chat_session = self.session_repo.get_session_by_code(session_code)
        if chat_session is None or chat_session.tenant_id != tenant.id:
            raise NotFoundError("session not found")

        # 会话状态检查
        self.guard.check_session_active(chat_session.status)

        # 保存用户消息
        user_msg = self.message_repo.create_message(
            tenant_id=tenant.id,
            session_id=chat_session.id,
            message_code=generate_message_code(),
            role="user",
            message_type="text",
            content=content,
            content_json=None,
        )
        self.message_repo.touch_session(chat_session, utcnow())
        self.db.commit()
        self.db.refresh(user_msg)

        return tenant, chat_session, user_msg

    # ---------- 流式前置校验（在 StreamingResponse 之前调用） ----------

    def pre_validate_stream(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
        request_id: str | None = None,
    ) -> None:
        """
        流式问答的前置校验。在 API 层创建 StreamingResponse 之前调用，
        确保 Guard 异常能被 FastAPI 异常处理器捕获并返回结构化 JSON 错误。
        """
        self.guard.check_content_length(content)

        tenant = self.session_repo.get_tenant_by_code(tenant_code)
        if tenant is None:
            raise NotFoundError("tenant not found")

        chat_session = self.session_repo.get_session_by_code(session_code)
        if chat_session is None or chat_session.tenant_id != tenant.id:
            raise NotFoundError("session not found")

        self.guard.check_session_active(chat_session.status)

    # ---------- 同步问答 ----------

    async def chat(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
        model: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        # 前置防护
        self.guard.check_content_length(content)
        await self.guard.check_idempotency(request_id)

        tenant, chat_session, user_msg = self._validate_and_save_user_message(
            tenant_code, session_code, content,
        )

        await self.guard.check_rate_limit(tenant_code, str(chat_session.user_id))
        await self.guard.acquire_session_lock(session_code)
        try:
            # 构建上下文
            context = self.context_mgr.build_context(chat_session.id)
            messages = self.prompt_builder.build(context)

            # 记录 llm_started 事件
            self.event_repo.create_event(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_id=user_msg.id,
                event_type="llm_started",
                payload={"model": model, "context_length": len(messages)},
            )
            self.db.commit()

            # 调用 LLM
            request = ChatRequest(model=model or "", messages=messages)
            response = await self.llm.chat(request)

            # 保存 assistant 消息
            assistant_msg = self.message_repo.create_message(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_code=generate_message_code(),
                role="assistant",
                message_type="text",
                content=response.content,
                content_json={
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                },
            )
            assistant_msg.status = "completed"
            self.message_repo.touch_session(chat_session, utcnow())

            # 记录 llm_finished 事件
            self.event_repo.create_event(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_id=assistant_msg.id,
                event_type="llm_finished",
                payload={
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                    "total_tokens": response.total_tokens,
                },
            )
            self.db.commit()
            self.db.refresh(assistant_msg)

            # 记录 token 用量
            await self.token_tracker.record_usage(
                tenant_code=tenant_code,
                model=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
            )

            return {
                "message_code": assistant_msg.message_code,
                "role": "assistant",
                "content": response.content,
                "finish_reason": response.finish_reason,
            }
        finally:
            await self.guard.release_session_lock(session_code)

    # ---------- 流式问答 ----------

    async def chat_stream(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
        model: str | None = None,
        request_id: str | None = None,
    ) -> AsyncIterator[dict]:
        # 前置防护
        self.guard.check_content_length(content)
        await self.guard.check_idempotency(request_id)

        tenant, chat_session, user_msg = self._validate_and_save_user_message(
            tenant_code, session_code, content,
        )

        await self.guard.check_rate_limit(tenant_code, str(chat_session.user_id))
        await self.guard.acquire_session_lock(session_code)

        try:
            # 构建上下文
            context = self.context_mgr.build_context(chat_session.id)
            messages = self.prompt_builder.build(context)
            assistant_message_code = generate_message_code()

            # 记录 llm_started 事件
            self.event_repo.create_event(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_id=user_msg.id,
                event_type="llm_started",
                payload={"model": model, "context_length": len(messages)},
            )
            self.db.commit()

            # 发送 start 事件
            yield {"event": "start", "data": {"message_code": assistant_message_code}}

            # 调用 LLM 流式
            request = ChatRequest(model=model or "", messages=messages, stream=True)

            full_content = ""
            finish_reason = "stop"

            async for delta in self.llm.chat_stream(request):
                if delta.content:
                    full_content += delta.content
                    yield {"event": "delta", "data": {"content": delta.content}}
                if delta.finish_reason:
                    finish_reason = delta.finish_reason

            # 保存 assistant 消息
            assistant_msg = self.message_repo.create_message(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_code=assistant_message_code,
                role="assistant",
                message_type="text",
                content=full_content,
                content_json={"finish_reason": finish_reason},
            )
            assistant_msg.status = "completed"
            self.message_repo.touch_session(chat_session, utcnow())

            # 记录 llm_finished 事件
            self.event_repo.create_event(
                tenant_id=tenant.id,
                session_id=chat_session.id,
                message_id=assistant_msg.id,
                event_type="llm_finished",
                payload={"finish_reason": finish_reason},
            )
            self.db.commit()

            # 记录 token 用量（流式无法精确获取 token 数，按字符粗估）
            estimated_completion = max(len(full_content) // 2, 1)
            await self.token_tracker.record_usage(
                tenant_code=tenant_code,
                model=model or self.settings.llm_default_model,
                prompt_tokens=0,
                completion_tokens=estimated_completion,
            )

            # 发送 done 事件
            yield {"event": "done", "data": {"finish_reason": finish_reason}}
        except Exception as exc:
            logger.exception("stream error: %s", exc)
            yield {"event": "error", "data": {"code": 50000, "message": str(exc)}}
        finally:
            await self.guard.release_session_lock(session_code)
