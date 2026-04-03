from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # system / user / assistant
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
    finish_reason: str  # stop / length / error
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
        """非流式聊天"""
        ...

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        """流式聊天，逐 token 返回"""
        ...
