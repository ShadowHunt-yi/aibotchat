from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest as ChatRequestSchema
from app.schemas.chat import ChatResponse as ChatResponseSchema
from app.schemas.common import APIResponse, success_response
from app.services.conversation.orchestrator import ConversationOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_redis(request: Request):
    return getattr(request.app.state, "redis", None)


async def _sse_generator(orchestrator: ConversationOrchestrator, payload: ChatRequestSchema):
    """将 orchestrator 的流式输出转为 SSE 文本"""
    async for event in orchestrator.chat_stream(
        tenant_code=payload.tenant_code,
        session_code=payload.session_code,
        content=payload.message.content,
        model=payload.model,
        request_id=payload.request_id,
    ):
        event_type = event["event"]
        data = json.dumps(event["data"], ensure_ascii=False)
        yield f"event: {event_type}\ndata: {data}\n\n"


@router.post("", response_model=APIResponse[ChatResponseSchema])
async def chat(
    payload: ChatRequestSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    redis_client = _get_redis(request)
    orchestrator = ConversationOrchestrator(db, redis_client=redis_client)

    if payload.stream:
        # 前置校验：在创建 StreamingResponse 之前执行，
        # 确保 Guard 异常能被 FastAPI 异常处理器正常捕获并返回结构化 JSON 错误。
        # 如果放到 generator 内部，异常发生时响应头可能已发送，客户端只会看到连接中断。
        orchestrator.pre_validate_stream(
            tenant_code=payload.tenant_code,
            session_code=payload.session_code,
            content=payload.message.content,
            request_id=payload.request_id,
        )

        return StreamingResponse(
            _sse_generator(orchestrator, payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = await orchestrator.chat(
        tenant_code=payload.tenant_code,
        session_code=payload.session_code,
        content=payload.message.content,
        model=payload.model,
        request_id=payload.request_id,
    )
    return success_response(ChatResponseSchema(**result))
