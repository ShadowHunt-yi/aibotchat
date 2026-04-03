# AI 客服中台 MVP 第二周开发详情

## 1. 第二周目标

第二周的目标是**打通从用户消息输入到模型回复输出的完整问答链路**，让系统从"能存消息"升级为"能对话"。到第二周结束时，系统应具备以下能力：

- 用户发送消息后，系统能调用大模型生成回复
- 支持多轮对话上下文拼接
- 支持 HTTP 同步问答（非流式）
- 支持 SSE 流式输出
- assistant 回复消息自动落库
- 关键链路事件写入 `message_events` 表
- 会话历史消息可查询
- LLM 调用层与业务逻辑解耦，后续可替换模型供应商

第二周完成后，Demo 客户端就可以完成一次真正的多轮 AI 对话体验。

---

## 2. 第二周开发边界

### 2.1 本周要做

- LLM Gateway 抽象层（统一模型调用接口）
- 至少接入一个模型供应商（推荐 OpenAI 兼容协议）
- Conversation Orchestrator（问答编排器）
- 多轮上下文拼接逻辑
- Prompt Builder（系统提示词拼装）
- 同步问答接口（非流式）
- SSE 流式输出接口
- assistant 消息落库
- message_events 事件记录
- 会话历史消息查询接口
- 新增 LLM 相关配置项
- **基础安全防护**：频率限流、消息长度限制、并发锁、幂等控制、token 用量追踪

### 2.2 本周不做

- 不做知识库检索（RAG）
- 不做工具调用（Function Calling）
- 不做意图路由（统一走 LLM）
- 不做 WebSocket 长连接
- 不做上下文摘要压缩
- 不做多模型路由策略
- 不做复杂多层级限流策略（如按 IP / 按接口差异化限流）
- 不做完整计费系统

---

## 3. 第二周交付结果

- 发送消息后可以收到 AI 回复（同步）
- 发送消息后可以收到 AI 流式回复（SSE）
- 多轮对话上下文生效
- assistant 消息自动写入数据库
- 关键事件（llm_started / llm_finished 等）可在 message_events 表中查询
- 会话历史接口可返回完整对话记录
- LLM Gateway 与业务代码解耦，替换供应商不需改业务逻辑
- 恶意刷请求会被限流拦截
- 同一会话不会被并发请求轰炸 LLM
- 每次 LLM 调用的 token 消耗有记录可查

---

## 4. 新增目录结构

在第一周已有目录基础上，新增以下文件：

```text
app/
  api/v1/
    chat.py                          ← 新增：问答入口（同步 + SSE）
    history.py                       ← 新增：会话历史查询
  core/
    guards.py                        ← 新增：安全防护（限流 / 并发锁 / 幂等）
  services/
    conversation/
      __init__.py
      orchestrator.py                ← 新增：问答编排主逻辑
      context_manager.py             ← 新增：上下文拼接
      prompt_builder.py              ← 新增：系统提示词构造
    llm/
      __init__.py
      base.py                        ← 新增：LLM 抽象基类
      openai_provider.py             ← 新增：OpenAI 兼容实现
    token_tracker.py                 ← 新增：token 用量追踪
  schemas/
    chat.py                          ← 新增：问答请求/响应/SSE 事件
    history.py                       ← 新增：历史查询响应
  db/
    repositories/
      event_repo.py                  ← 新增：message_events 仓储
```

完整目录关系：

```text
app/
  api/v1/
    router.py                       （修改：注册新路由）
    health.py
    sessions.py
    messages.py
    chat.py                          ← 新增
    history.py                       ← 新增
  core/
    config.py                        （修改：新增 LLM + 防护配置项）
    logger.py
    middleware.py
    security.py
    exception_handlers.py            （修改：新增 LLMError / RateLimitError）
    guards.py                        ← 新增：安全防护
  db/
    base.py
    session.py
    models/
      ...（不变）
    repositories/
      session_repo.py                （修改：新增历史查询方法）
      message_repo.py                （修改：新增 assistant 消息写入）
      event_repo.py                  ← 新增
  schemas/
    common.py
    session.py
    message.py
    chat.py                          ← 新增
    history.py                       ← 新增
  services/
    session_service.py
    message_service.py
    conversation/                    ← 新增目录
      __init__.py
      orchestrator.py
      context_manager.py
      prompt_builder.py
    llm/                             ← 新增目录
      __init__.py
      base.py
      openai_provider.py
    token_tracker.py                 ← 新增：token 用量追踪
  utils/
    ids.py
    time.py
  tests/
    api/
      test_chat.py                   ← 新增
      test_history.py                ← 新增
    services/
      test_orchestrator.py           ← 新增
      test_llm_gateway.py            ← 新增
```

---

## 5. 核心模块设计

### 5.1 LLM Gateway

LLM Gateway 是模型调用的抽象层，所有业务代码通过它与模型交互，不直接依赖任何供应商 SDK。

#### 5.1.1 抽象基类

```python
# app/services/llm/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import AsyncIterator


@dataclass
class ChatMessage:
    role: str          # system / user / assistant
    content: str


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatResponse:
    content: str
    model: str
    finish_reason: str             # stop / length / error
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatDelta:
    content: str
    finish_reason: str | None = None


class LLMProvider(ABC):
    """LLM 供应商抽象基类"""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """同步（非流式）聊天"""
        ...

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        """流式聊天，逐 token 返回"""
        ...
```

#### 5.1.2 OpenAI 兼容实现

推荐使用 `httpx` 直接调用 OpenAI 兼容 API（不强绑 `openai` SDK），便于接入 DeepSeek、通义千问、月之暗面等兼容接口。

```python
# app/services/llm/openai_provider.py

import json
import httpx
from collections.abc import AsyncIterator

from app.services.llm.base import (
    ChatDelta, ChatMessage, ChatRequest, ChatResponse, LLMProvider,
)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, default_model: str, timeout: float = 60.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def _build_payload(self, request: ChatRequest) -> dict:
        return {
            "model": request.model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, request: ChatRequest) -> ChatResponse:
        request.stream = False
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._build_payload(request),
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ChatResponse(
            content=choice["message"]["content"],
            model=data.get("model", request.model),
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        request.stream = True
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._build_payload(request),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[len("data: "):]
                    if payload.strip() == "[DONE]":
                        return
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {})
                    finish = chunk["choices"][0].get("finish_reason")
                    yield ChatDelta(
                        content=delta.get("content", ""),
                        finish_reason=finish,
                    )
```

#### 5.1.3 Provider 工厂

```python
# app/services/llm/__init__.py

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import OpenAIProvider

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        _provider = OpenAIProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            default_model=settings.llm_default_model,
            timeout=settings.llm_timeout,
        )
    return _provider
```

### 5.2 Context Manager（上下文管理）

职责：

- 从数据库加载指定 session 的历史消息
- 按角色和时间排序
- 裁剪上下文窗口（限制最近 N 轮或 max_tokens）
- 返回标准 `ChatMessage` 列表

```python
# app/services/conversation/context_manager.py

from sqlalchemy.orm import Session

from app.db.models.message import Message
from app.services.llm.base import ChatMessage


class ContextManager:
    def __init__(self, db: Session, max_rounds: int = 20):
        self.db = db
        self.max_rounds = max_rounds

    def build_context(self, session_id: int) -> list[ChatMessage]:
        """加载最近 N 轮对话，转换为 ChatMessage 列表"""
        messages = (
            self.db.query(Message)
            .filter(
                Message.session_id == session_id,
                Message.role.in_(["user", "assistant"]),
                Message.status.in_(["accepted", "completed"]),
            )
            .order_by(Message.created_at.asc())
            .all()
        )

        # 只保留最近 max_rounds 轮（一轮 = user + assistant）
        if len(messages) > self.max_rounds * 2:
            messages = messages[-(self.max_rounds * 2):]

        return [
            ChatMessage(role=m.role, content=m.content or "")
            for m in messages
        ]
```

### 5.3 Prompt Builder（提示词构造）

职责：

- 拼装 system prompt
- 将 system prompt 与上下文消息合并
- 后续可扩展注入知识片段、工具定义等

```python
# app/services/conversation/prompt_builder.py

from app.services.llm.base import ChatMessage

DEFAULT_SYSTEM_PROMPT = """你是一个专业的 AI 客服助手。请遵守以下规则：
1. 用中文回答用户问题，语气友好专业
2. 如果你不确定答案，请诚实告知，不要编造
3. 回答要简洁有条理
4. 涉及退款、赔付、法律等敏感问题时，建议用户联系人工客服"""


class PromptBuilder:
    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def build(self, context_messages: list[ChatMessage]) -> list[ChatMessage]:
        """将 system prompt 与上下文拼装为完整消息列表"""
        return [
            ChatMessage(role="system", content=self.system_prompt),
            *context_messages,
        ]
```

### 5.4 Conversation Orchestrator（问答编排器）

这是第二周的**核心模块**，负责：

1. 接收用户消息
2. 保存用户消息到数据库
3. 加载上下文
4. 拼装 prompt
5. 调用 LLM（同步或流式）
6. 保存 assistant 回复到数据库
7. 写入 message_events

```python
# app/services/conversation/orchestrator.py

import logging
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.core.exception_handlers import NotFoundError
from app.db.repositories.event_repo import EventRepository
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.session_repo import SessionRepository
from app.services.conversation.context_manager import ContextManager
from app.services.conversation.prompt_builder import PromptBuilder
from app.services.llm import get_llm_provider
from app.services.llm.base import ChatRequest, ChatResponse, ChatDelta
from app.utils.ids import generate_message_code
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.event_repo = EventRepository(db)
        self.context_mgr = ContextManager(db)
        self.prompt_builder = PromptBuilder()
        self.llm = get_llm_provider()

    # ---------- 公共：校验 + 保存用户消息 ----------

    def _validate_and_save_user_message(
        self, tenant_code: str, session_code: str, content: str,
    ) -> tuple:
        """校验 tenant/session，保存用户消息，返回 (tenant, session, user_message)"""
        tenant = self.session_repo.get_tenant_by_code(tenant_code)
        if tenant is None:
            raise NotFoundError("tenant not found")

        chat_session = self.session_repo.get_session_by_code(session_code)
        if chat_session is None or chat_session.tenant_id != tenant.id:
            raise NotFoundError("session not found")

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

    # ---------- 同步问答 ----------

    async def chat(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
        model: str | None = None,
    ) -> dict:
        tenant, chat_session, user_msg = self._validate_and_save_user_message(
            tenant_code, session_code, content,
        )

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
        request = ChatRequest(
            model=model or "",
            messages=messages,
        )
        response: ChatResponse = await self.llm.chat(request)

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

        return {
            "message_code": assistant_msg.message_code,
            "role": "assistant",
            "content": response.content,
            "finish_reason": response.finish_reason,
        }

    # ---------- 流式问答 ----------

    async def chat_stream(
        self,
        tenant_code: str,
        session_code: str,
        content: str,
        model: str | None = None,
    ) -> AsyncIterator[dict]:
        tenant, chat_session, user_msg = self._validate_and_save_user_message(
            tenant_code, session_code, content,
        )

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
        request = ChatRequest(
            model=model or "",
            messages=messages,
            stream=True,
        )

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

        # 发送 done 事件
        yield {"event": "done", "data": {"finish_reason": finish_reason}}
```

---

## 6. API 设计

### 6.1 同步问答

`POST /api/v1/chat`

请求：

```json
{
  "tenant_code": "demo_tenant",
  "session_code": "s_202603260001",
  "message": {
    "type": "text",
    "content": "你好，我的订单什么时候到？"
  },
  "stream": false,
  "request_id": "req_001"
}
```

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "message_code": "m_202603260002",
    "role": "assistant",
    "content": "您好！请提供您的订单号，我来帮您查询物流状态。",
    "finish_reason": "stop"
  },
  "trace_id": "trace_xxx"
}
```

### 6.2 SSE 流式问答

`POST /api/v1/chat`（`stream: true`）

请求与上面相同，只是 `stream` 设为 `true`。

返回 `text/event-stream`：

```text
event: start
data: {"message_code":"m_202603260002"}

event: delta
data: {"content":"您好！"}

event: delta
data: {"content":"请提供您的订单号，"}

event: delta
data: {"content":"我来帮您查询物流状态。"}

event: done
data: {"finish_reason":"stop"}
```

### 6.3 会话历史查询

`GET /api/v1/sessions/{session_code}/messages`

查询参数：

- `limit`：每页条数，默认 50
- `offset`：偏移量，默认 0

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "session_code": "s_202603260001",
    "items": [
      {
        "message_code": "m_1",
        "role": "user",
        "content": "你好",
        "status": "accepted",
        "created_at": "2026-03-26T10:00:00Z"
      },
      {
        "message_code": "m_2",
        "role": "assistant",
        "content": "您好！有什么可以帮您的吗？",
        "status": "completed",
        "created_at": "2026-03-26T10:00:02Z"
      }
    ],
    "total": 2
  },
  "trace_id": "trace_xxx"
}
```

---

## 7. Schema 定义

### 7.1 `app/schemas/chat.py`

```python
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatMessagePayload(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    session_code: str = Field(min_length=1, max_length=64)
    message: ChatMessagePayload
    stream: bool = False
    model: str | None = None
    request_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    message_code: str
    role: str
    content: str
    finish_reason: str
```

### 7.2 `app/schemas/history.py`

```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    message_code: str
    role: str
    content: str | None
    status: str
    created_at: datetime


class HistoryResponse(BaseModel):
    session_code: str
    items: list[HistoryMessage]
    total: int
```

---

## 8. 配置变更

### 8.1 `config.py` 新增字段

在 `Settings` 类中新增以下配置：

```python
# LLM 相关配置
llm_provider: str = "openai"                        # 供应商标识
llm_api_key: str = ""                               # API Key
llm_base_url: str = "https://api.openai.com/v1"     # API Base URL
llm_default_model: str = "gpt-4o-mini"              # 默认模型
llm_timeout: float = 60.0                           # 超时秒数
llm_max_context_rounds: int = 20                    # 最大上下文轮数
```

### 8.2 `.env.example` 新增

```env
# LLM
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_TIMEOUT=60
LLM_MAX_CONTEXT_ROUNDS=20

# Guards / Rate Limiting
GUARD_MAX_REQUESTS_PER_MINUTE=20
GUARD_MAX_MESSAGE_LENGTH=4000
GUARD_SESSION_LOCK_ENABLED=true
GUARD_IDEMPOTENCY_ENABLED=true
GUARD_IDEMPOTENCY_TTL=300
```

支持接入 OpenAI 兼容协议的任何供应商，只需修改 `LLM_BASE_URL` 和 `LLM_API_KEY`：

| 供应商 | LLM_BASE_URL 示例 |
|--------|-------------------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 月之暗面 | `https://api.moonshot.cn/v1` |
| 本地 Ollama | `http://localhost:11434/v1` |

---

## 9. 新增 Repository

### 9.1 `event_repo.py`

```python
# app/db/repositories/event_repo.py

from sqlalchemy.orm import Session
from app.db.models.message_event import MessageEvent


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._seq_cache: dict[int, int] = {}

    def _next_seq(self, session_id: int) -> int:
        if session_id not in self._seq_cache:
            last = (
                self.db.query(MessageEvent)
                .filter(MessageEvent.session_id == session_id)
                .order_by(MessageEvent.event_seq.desc())
                .first()
            )
            self._seq_cache[session_id] = (last.event_seq if last else 0)
        self._seq_cache[session_id] += 1
        return self._seq_cache[session_id]

    def create_event(
        self,
        *,
        tenant_id: int,
        session_id: int,
        message_id: int | None,
        event_type: str,
        payload: dict,
    ) -> MessageEvent:
        event = MessageEvent(
            tenant_id=tenant_id,
            session_id=session_id,
            message_id=message_id,
            event_type=event_type,
            event_seq=self._next_seq(session_id),
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()
        return event
```

### 9.2 `message_repo.py` 新增方法

在已有 `MessageRepository` 中新增：

```python
def list_messages(
    self,
    session_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Message], int]:
    """返回会话消息列表和总数"""
    query = (
        self.db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total
```

### 9.3 `session_repo.py` 新增方法

在已有 `SessionRepository` 中新增：

```python
def get_session_with_tenant(self, session_code: str, tenant_code: str) -> ChatSession | None:
    """通过 session_code 和 tenant_code 联合查询"""
    return (
        self.db.query(ChatSession)
        .join(Tenant, ChatSession.tenant_id == Tenant.id)
        .filter(
            ChatSession.session_code == session_code,
            Tenant.tenant_code == tenant_code,
        )
        .one_or_none()
    )
```

---

## 10. 安全防护设计

第二周是 LLM 调用真正上线的节点。没有任何防护的情况下，一个恶意用户可以：

- 高频发请求刷光 API token 预算
- 发送超长文本让上下文撑满模型窗口
- 对同一 session 并发发送请求，产生重复 LLM 调用
- 用相同 request_id 重复提交
- 在已关闭的 session 上继续发消息

第二周需要加入**最小够用**的防护层，不追求完整的风控体系，但要把最容易被利用的漏洞堵住。

### 10.1 防护策略总览

| 防护点 | 策略 | 实现位置 |
|--------|------|----------|
| 请求频率限制 | 滑动窗口限流（Redis） | `guards.py` |
| 消息内容长度 | 单条消息最大字符数限制 | Schema 校验 + `guards.py` |
| 会话并发锁 | 同一 session 同时只能有一个 LLM 请求在执行 | `guards.py`（Redis SETNX） |
| 请求幂等 | request_id 去重，防止重复提交 | `guards.py`（Redis SETNX） |
| 会话状态校验 | 只有 `active` 状态的 session 允许问答 | Orchestrator |
| 输出 token 上限 | LLM 请求中限制 `max_tokens` | LLM Gateway |
| token 用量追踪 | 每次调用记录消耗，按租户累计 | `token_tracker.py` |

### 10.2 `app/core/guards.py` 实现

```python
# app/core/guards.py

import logging
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.exception_handlers import AppError

logger = logging.getLogger(__name__)


class RateLimitExceeded(AppError):
    """请求频率超限"""
    def __init__(self) -> None:
        super().__init__(
            "rate limit exceeded, please try again later",
            code=42900,
            status_code=429,
        )


class ConcurrentRequestBlocked(AppError):
    """同一会话并发请求被拦截"""
    def __init__(self) -> None:
        super().__init__(
            "another request is being processed in this session",
            code=42901,
            status_code=429,
        )


class DuplicateRequestError(AppError):
    """重复请求"""
    def __init__(self) -> None:
        super().__init__(
            "duplicate request",
            code=40901,
            status_code=409,
        )


class SessionNotActiveError(AppError):
    """会话非活跃状态"""
    def __init__(self, status: str) -> None:
        super().__init__(
            f"session is {status}, cannot send messages",
            code=40301,
            status_code=403,
        )


class ContentTooLongError(AppError):
    """消息内容过长"""
    def __init__(self, max_length: int) -> None:
        super().__init__(
            f"message content exceeds maximum length of {max_length} characters",
            code=42201,
            status_code=422,
        )


class ChatGuard:
    """
    问答请求的安全防护层。
    在 Orchestrator 调用 LLM 之前执行所有检查。
    """

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client
        self.settings = get_settings()

    # ---- 1. 频率限流（滑动窗口） ----

    async def check_rate_limit(self, tenant_code: str, user_id: str) -> None:
        """
        基于 Redis 滑动窗口的频率限制。
        限制维度：tenant + user，粒度：每分钟 N 次请求。
        """
        if self.redis is None:
            return

        key = f"rate_limit:chat:{tenant_code}:{user_id}"
        max_rpm = self.settings.guard_max_requests_per_minute

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 60 秒窗口
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
        """
        对同一 session 加互斥锁，防止并发 LLM 请求。
        锁的超时时间 = LLM 最大超时 + 缓冲。
        """
        if self.redis is None:
            return True

        key = f"chat_lock:{session_code}"
        lock_ttl = int(self.settings.llm_timeout) + 10  # LLM 超时 + 10 秒缓冲
        acquired = await self.redis.set(key, "1", nx=True, ex=lock_ttl)

        if not acquired:
            raise ConcurrentRequestBlocked()
        return True

    async def release_session_lock(self, session_code: str) -> None:
        """释放会话锁"""
        if self.redis is None:
            return
        key = f"chat_lock:{session_code}"
        await self.redis.delete(key)

    # ---- 3. 请求幂等 ----

    async def check_idempotency(self, request_id: str | None) -> None:
        """
        基于 request_id 的幂等检查。
        同一 request_id 在 5 分钟内只允许处理一次。
        """
        if request_id is None or self.redis is None:
            return

        key = f"idempotent:chat:{request_id}"
        is_new = await self.redis.set(key, "1", nx=True, ex=300)  # 5 分钟过期

        if not is_new:
            raise DuplicateRequestError()

    # ---- 4. 消息长度检查 ----

    def check_content_length(self, content: str) -> None:
        """检查单条消息内容长度"""
        max_length = self.settings.guard_max_message_length
        if len(content) > max_length:
            raise ContentTooLongError(max_length)

    # ---- 5. 会话状态检查 ----

    def check_session_active(self, session_status: str) -> None:
        """只有 active 状态的 session 允许问答"""
        if session_status != "active":
            raise SessionNotActiveError(session_status)
```

### 10.3 `app/services/token_tracker.py` 实现

```python
# app/services/token_tracker.py

import logging
from datetime import datetime

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TokenTracker:
    """
    追踪 LLM token 用量。
    - 按 tenant 维度，按天累计
    - 数据存入 Redis，key 自动过期（保留 7 天）
    - 同时在 message_events 中记录每次调用的精确用量
    """

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis = redis_client

    async def record_usage(
        self,
        tenant_code: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict:
        """记录一次 LLM 调用的 token 消耗，返回当日累计"""
        total = prompt_tokens + completion_tokens
        today = datetime.utcnow().strftime("%Y%m%d")

        if self.redis is None:
            return {"today_total": total}

        # 按 tenant + 日期累计
        key_total = f"token_usage:{tenant_code}:{today}:total"
        key_prompt = f"token_usage:{tenant_code}:{today}:prompt"
        key_completion = f"token_usage:{tenant_code}:{today}:completion"
        key_calls = f"token_usage:{tenant_code}:{today}:calls"

        pipe = self.redis.pipeline()
        pipe.incrby(key_total, total)
        pipe.incrby(key_prompt, prompt_tokens)
        pipe.incrby(key_completion, completion_tokens)
        pipe.incr(key_calls)
        # 7 天自动过期
        for k in [key_total, key_prompt, key_completion, key_calls]:
            pipe.expire(k, 7 * 86400)
        results = await pipe.execute()

        today_total = results[0]

        logger.info(
            "token usage: tenant=%s model=%s prompt=%d completion=%d total=%d today_cumulative=%d",
            tenant_code, model, prompt_tokens, completion_tokens, total, today_total,
        )

        return {"today_total": today_total}

    async def get_daily_usage(self, tenant_code: str, date: str | None = None) -> dict:
        """查询某天的 token 用量"""
        if self.redis is None:
            return {"total": 0, "prompt": 0, "completion": 0, "calls": 0}

        day = date or datetime.utcnow().strftime("%Y%m%d")
        pipe = self.redis.pipeline()
        pipe.get(f"token_usage:{tenant_code}:{day}:total")
        pipe.get(f"token_usage:{tenant_code}:{day}:prompt")
        pipe.get(f"token_usage:{tenant_code}:{day}:completion")
        pipe.get(f"token_usage:{tenant_code}:{day}:calls")
        results = await pipe.execute()

        return {
            "total": int(results[0] or 0),
            "prompt": int(results[1] or 0),
            "completion": int(results[2] or 0),
            "calls": int(results[3] or 0),
        }
```

### 10.4 防护层集成到 Orchestrator

在 `ConversationOrchestrator` 中，LLM 调用前后加入防护：

```python
# orchestrator.py 中的 chat() 方法改造示意

async def chat(self, tenant_code, session_code, content, model=None, request_id=None):
    # ===== 第一关：前置防护 =====
    self.guard.check_content_length(content)                       # 消息长度
    await self.guard.check_rate_limit(tenant_code, user_id)        # 频率限流
    await self.guard.check_idempotency(request_id)                 # 幂等检查
    self.guard.check_session_active(chat_session.status)           # 会话状态

    # ===== 第二关：并发锁 =====
    await self.guard.acquire_session_lock(session_code)
    try:
        # ... 保存用户消息、构建上下文、调用 LLM、保存回复 ...

        # ===== 第三关：记录用量 =====
        await self.token_tracker.record_usage(
            tenant_code=tenant_code,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
        )
    finally:
        await self.guard.release_session_lock(session_code)

    return result
```

执行顺序：

```text
请求进入
  │
  ├─ 1. 消息长度检查（同步，无 IO）
  ├─ 2. 频率限流检查（Redis INCR）
  ├─ 3. 幂等检查（Redis SETNX）
  ├─ 4. 会话状态检查（DB 查询，已有逻辑中顺带做）
  ├─ 5. 并发锁获取（Redis SETNX）
  │
  ├─ [保存用户消息]
  ├─ [构建上下文]
  ├─ [调用 LLM]
  ├─ [保存 assistant 消息]
  ├─ [记录 token 用量]
  │
  └─ 6. 释放并发锁
```

### 10.5 配置项

在 `Settings` 中新增防护相关配置：

```python
# 防护相关
guard_max_requests_per_minute: int = 20          # 每用户每分钟最大请求数
guard_max_message_length: int = 4000             # 单条消息最大字符数
guard_session_lock_enabled: bool = True          # 是否启用会话并发锁
guard_idempotency_enabled: bool = True           # 是否启用幂等检查
guard_idempotency_ttl: int = 300                 # 幂等 key 过期秒数
```

对应 `.env.example` 新增：

```env
# Guards / Rate Limiting
GUARD_MAX_REQUESTS_PER_MINUTE=20
GUARD_MAX_MESSAGE_LENGTH=4000
GUARD_SESSION_LOCK_ENABLED=true
GUARD_IDEMPOTENCY_ENABLED=true
GUARD_IDEMPOTENCY_TTL=300
```

### 10.6 Redis 连接初始化

防护层和 token 追踪依赖 Redis 异步客户端。在 `app/main.py` 的 `lifespan` 中初始化：

```python
import redis.asyncio as aioredis

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    if settings.app_auto_create_tables:
        init_db()

    # 初始化 Redis 异步连接
    redis_client = aioredis.from_url(settings.resolved_redis_url, decode_responses=True)
    app.state.redis = redis_client

    yield

    # 关闭 Redis
    await redis_client.close()
```

通过 `request.app.state.redis` 在路由中获取，注入到 Guard 和 TokenTracker。

### 10.7 Schema 层增强

在 `ChatMessagePayload` 中增加 `max_length` 校验作为第一道防线：

```python
class ChatMessagePayload(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(min_length=1, max_length=4000)  # Schema 层硬限制
```

### 10.8 错误码汇总

| 错误码 | HTTP 状态码 | 含义 |
|--------|------------|------|
| 42900  | 429        | 请求频率超限 |
| 42901  | 429        | 会话并发请求被拦截 |
| 40901  | 409        | 重复请求（request_id 相同） |
| 40301  | 403        | 会话非活跃状态 |
| 42201  | 422        | 消息内容过长 |
| 50200  | 502        | LLM 调用失败 |
| 50400  | 504        | LLM 调用超时 |

### 10.9 防护层降级策略

**Redis 不可用时的处理**：所有 Redis 依赖的检查（限流、并发锁、幂等）在 `redis_client is None` 时自动跳过，不阻断正常业务。这是有意为之——MVP 阶段宁可没有防护也不要因为 Redis 故障导致整个问答服务不可用。

生产环境上线后，建议改为 Redis 不可用时拒绝请求（fail-closed），或加独立的 Redis Sentinel / Cluster。

---

## 11. 异常处理扩展

在 `exception_handlers.py` 中新增 LLM 相关异常：

```python
class LLMError(AppError):
    """大模型调用异常"""
    def __init__(self, message: str) -> None:
        super().__init__(message, code=50200, status_code=status.HTTP_502_BAD_GATEWAY)


class LLMTimeoutError(AppError):
    """大模型超时"""
    def __init__(self) -> None:
        super().__init__("llm request timeout", code=50400, status_code=status.HTTP_504_GATEWAY_TIMEOUT)
```

在 `OpenAIProvider` 中捕获 `httpx` 异常并转换为上述业务异常。

---

## 11. SSE 实现要点

### 11.1 FastAPI SSE 返回方式

使用 `StreamingResponse` 配合 `async generator`：

```python
# app/api/v1/chat.py

import json
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest as ChatRequestSchema, ChatResponse as ChatResponseSchema
from app.schemas.common import APIResponse, success_response
from app.services.conversation.orchestrator import ConversationOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


async def _sse_generator(orchestrator, payload):
    """将 orchestrator 的流式输出转为 SSE 文本"""
    async for event in orchestrator.chat_stream(
        tenant_code=payload.tenant_code,
        session_code=payload.session_code,
        content=payload.message.content,
        model=payload.model,
    ):
        event_type = event["event"]
        data = json.dumps(event["data"], ensure_ascii=False)
        yield f"event: {event_type}\ndata: {data}\n\n"


@router.post("")
async def chat(
    payload: ChatRequestSchema,
    db: Session = Depends(get_db),
):
    orchestrator = ConversationOrchestrator(db)

    if payload.stream:
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
    )
    return success_response(ChatResponseSchema(**result))
```

### 11.2 SSE 注意事项

- 响应头 `Content-Type` 必须为 `text/event-stream`
- 设置 `Cache-Control: no-cache` 和 `X-Accel-Buffering: no`（避免 Nginx 缓冲）
- 每个事件以 `\n\n` 结尾
- 如果 LLM 调用失败，在流中发送 `error` 事件后关闭连接
- 流结束必须发送 `done` 事件

### 11.3 错误事件格式

```text
event: error
data: {"code":50200,"message":"model service unavailable"}
```

---

## 12. 依赖变更

### 12.1 `pyproject.toml` 新增依赖

```toml
dependencies = [
    ...
    "httpx>=0.28.1",       # 从 dev 提升到正式依赖（LLM HTTP 调用）
]
```

注意：`httpx` 当前仅在 `dev` 依赖组中，第二周需要提升为正式依赖，因为 `OpenAIProvider` 在生产环境需要它。

---

## 13. 第二周详细开发计划

建议按 5 个工作日安排。

### Day 1：LLM Gateway

任务：

- 新增 LLM 相关配置项（`config.py`、`.env.example`）
- 实现 `LLMProvider` 抽象基类
- 实现 `OpenAIProvider`（同步 + 流式）
- 实现 Provider 工厂方法
- 新增 `LLMError` / `LLMTimeoutError` 异常
- 编写 LLM Gateway 单元测试（mock HTTP 响应）

当天产出：

- 可以通过 `get_llm_provider().chat(request)` 调用模型
- 流式调用 `chat_stream()` 可逐 token 返回
- 替换 `LLM_BASE_URL` 即可切换供应商

### Day 2：上下文管理 + Prompt Builder + 安全防护

任务：

- 实现 `ContextManager`（加载历史消息、裁剪上下文）
- 实现 `PromptBuilder`（system prompt 拼装）
- 实现 `EventRepository`（message_events 写入）
- 实现 `ChatGuard`（限流 / 并发锁 / 幂等 / 内容检查）
- 实现 `TokenTracker`（token 用量追踪）
- 初始化 Redis 异步连接（`lifespan` 中）
- 新增防护相关配置项
- 编写上下文管理和防护层单元测试

当天产出：

- 给定 session_id，可获取最近 N 轮对话的 `ChatMessage` 列表
- system prompt 可拼装到消息最前面
- 事件可写入 message_events 表
- 频率限流、并发锁、幂等检查均可工作
- Redis 不可用时防护层自动降级不阻断业务

### Day 3：Conversation Orchestrator + 同步问答

任务：

- 实现 `ConversationOrchestrator`（集成 Guard + TokenTracker）
- 先实现 `chat()` 同步方法
- 实现 `POST /api/v1/chat`（`stream=false` 分支）
- 定义 `ChatRequest`、`ChatResponse` Schema
- 注册新路由到 `router.py`
- 端到端测试：创建会话 → 发消息 → 收回复
- 验证防护层：超频请求被拦截、重复 request_id 被拒绝

当天产出：

- `POST /api/v1/chat` 可完成完整同步问答
- assistant 消息已写入数据库
- message_events 有 `llm_started` / `llm_finished` 记录
- 恶意请求被正确拦截并返回对应错误码

### Day 4：SSE 流式输出

任务：

- 实现 `chat_stream()` 方法
- 实现 SSE generator
- 实现 `POST /api/v1/chat`（`stream=true` 分支）
- 流中发生错误时返回 `error` 事件
- 流结束后 assistant 消息落库
- 手动测试 SSE（curl / Postman / 浏览器 EventSource）

当天产出：

- 流式问答可用
- 可看到逐 token 返回效果
- 流结束后数据库中有完整 assistant 消息

验证命令：

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_code": "demo_tenant",
    "session_code": "你的session_code",
    "message": {"type": "text", "content": "你好"},
    "stream": true
  }'
```

### Day 5：会话历史 + 多轮验证 + 测试

任务：

- 实现 `GET /api/v1/sessions/{session_code}/messages` 历史接口
- 定义 `HistoryMessage`、`HistoryResponse` Schema
- `message_repo.py` 新增 `list_messages` 方法
- 端到端多轮对话验证（确认上下文正确传递）
- 编写完整测试用例
- 补充 README 中第二周新增接口说明

当天产出：

- 历史消息可查询
- 多轮对话上下文正确（第二轮回复能引用第一轮内容）
- 所有新增接口有测试覆盖
- README 更新

---

## 14. 测试建议

### 14.1 LLM Gateway 测试

- mock HTTP 响应，验证 `chat()` 返回格式正确
- mock SSE 流，验证 `chat_stream()` 逐 delta 返回
- 模拟超时，验证抛出 `LLMTimeoutError`
- 模拟 4xx/5xx，验证抛出 `LLMError`

### 14.2 Context Manager 测试

- 空 session 返回空列表
- 多条消息按时间排序返回
- 超过 `max_rounds` 时只保留最近的
- 只包含 `user` 和 `assistant` 角色

### 14.3 Orchestrator 测试

- 同步问答完整链路（mock LLM）
- assistant 消息写入数据库
- message_events 正确记录
- tenant/session 不存在时抛 404

### 14.4 Guard 防护层测试

- 连续发 N+1 次请求，第 N+1 次返回 429
- 同一 request_id 发两次，第二次返回 409
- 同一 session 并发发两个请求，第二个返回 429
- 向 `closed` 状态的 session 发消息，返回 403
- 消息内容超过 `max_length`，返回 422
- Redis 不可用时，防护层跳过不阻断正常请求

### 14.5 Token Tracker 测试

- 调用 `record_usage()` 后，Redis 中 key 值正确累加
- `get_daily_usage()` 返回正确的当日统计
- Redis 不可用时，`record_usage()` 不抛异常

### 14.6 API 测试

- `POST /api/v1/chat`（`stream=false`）返回 200 + 正确结构
- `POST /api/v1/chat`（`stream=true`）返回 `text/event-stream`
- `GET /api/v1/sessions/{code}/messages` 返回历史
- 参数校验失败返回 422
- 超长消息返回 422

### 14.7 集成测试

- 创建会话 → 发 3 条消息 → 查历史 → 验证 6 条记录（3 user + 3 assistant）
- 第 3 轮回复应体现前 2 轮对话上下文
- 高频发送验证限流生效

---

## 15. 第二周验收标准

第二周结束时，按以下清单验收：

**核心功能**

- `POST /api/v1/chat` 同步问答可用
- `POST /api/v1/chat` 流式问答可用（SSE）
- 多轮对话上下文生效（第 N 轮能引用前面内容）
- assistant 回复自动写入 `messages` 表
- `message_events` 表有 `llm_started` / `llm_finished` 事件
- `GET /api/v1/sessions/{code}/messages` 可返回完整对话历史
- LLM 配置可通过环境变量切换供应商和模型
- LLM 调用超时/失败有明确错误返回
- SSE 流异常时返回 `error` 事件

**安全防护**

- 同一用户超频请求返回 429
- 同一 session 并发请求返回 429
- 重复 request_id 返回 409
- 超长消息返回 422
- 非 active 状态 session 返回 403
- 每次 LLM 调用的 token 消耗有记录（Redis + message_events）
- Redis 不可用时防护降级不阻断业务

**工程质量**

- 所有新增接口有测试覆盖
- Swagger 文档包含新增接口
- 防护相关配置可通过环境变量调整

---

## 16. 关键风险与应对

### 16.1 LLM 调用延迟高

风险：大模型响应慢（3~10 秒），同步接口体验差。

应对：
- 默认推荐使用流式模式，先返回 `start` 事件让前端有响应
- 同步模式设置合理超时（60 秒）
- 超时后返回明确错误，不挂起连接

### 16.2 上下文窗口过长

风险：多轮对话后上下文 token 数超限。

应对：
- 第二周先用 `max_rounds` 做硬裁剪（默认 20 轮）
- 第三周再加基于 token 数的精确裁剪
- 后续可加摘要压缩

### 16.3 SSE 连接中断

风险：网络抖动导致 SSE 连接断开，assistant 消息未落库。

应对：
- 流中累积 `full_content`，流结束后统一落库
- 如果流异常中断，catch 异常后仍尝试保存已接收内容
- 前端可通过历史接口补偿查询

### 16.4 并发写入冲突

风险：同一 session 同时发多条消息，event_seq 冲突。

应对：
- 通过 `ChatGuard.acquire_session_lock()` 保证同一 session 串行执行
- 锁超时设置为 LLM 超时 + 10 秒缓冲
- 第二个请求直接返回 429，不排队等待

### 16.5 恶意刷 token

风险：用户高频发请求或发超长文本，短时间内消耗大量 API 额度。

应对：
- 滑动窗口限流（默认每用户每分钟 20 次）
- 单条消息最大 4000 字符
- LLM 请求 `max_tokens` 限制输出长度
- token 用量按租户按天累计到 Redis，可随时查询
- 后续可加租户级每日 token 预算上限（超限拒绝服务）

### 16.6 Redis 单点故障

风险：Redis 不可用导致限流、并发锁、幂等全部失效。

应对：
- MVP 阶段采用 fail-open 策略：Redis 不可用时跳过防护，保证业务不中断
- 生产环境建议改为 fail-closed 或接入 Redis Sentinel
- LLM 调用本身有超时控制，即使没有限流也不会无限消耗

---

## 17. 第二周结束后的状态

如果第二周按计划完成，那么系统已经具备：

- 完整的 AI 问答能力（同步 + 流式）
- 多轮对话上下文支持
- 全链路可追踪（message + message_events）
- 会话历史可回放
- 可替换的 LLM 供应商
- 基础安全防护（限流 / 并发锁 / 幂等 / 内容检查）
- token 用量可追踪

也就是说，第三周就可以专注做知识库检索（RAG），在 prompt 中注入知识片段，让客服从"能聊天"升级为"能回答专业问题"。

---

## 18. 建议的下一份文档

第二周文档完成后，下一步最适合继续细化的内容有两份：

1. `第三周开发详情：知识库能力（文档导入 / 切片 / embedding / 检索）`
2. `LLM Gateway 接口协议文档（含各供应商适配指南）`
