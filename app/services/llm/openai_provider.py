from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.core.exception_handlers import LLMError, LLMTimeoutError
from app.services.llm.base import (
    ChatDelta,
    ChatRequest,
    ChatResponse,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI 兼容协议实现（适用于 OpenAI / DeepSeek / 通义 / Moonshot / Ollama 等）"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: float = 60.0,
    ) -> None:
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
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._build_payload(request),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError()
        except httpx.HTTPStatusError as exc:
            logger.error("LLM HTTP error: %s %s", exc.response.status_code, exc.response.text[:500])
            raise LLMError(f"llm returned {exc.response.status_code}")
        except httpx.HTTPError as exc:
            logger.error("LLM request error: %s", exc)
            raise LLMError("llm service unavailable")

        choices = data.get("choices")
        if not choices:
            raise LLMError("llm returned empty choices")
        choice = choices[0]
        message = choice.get("message") or {}
        usage = data.get("usage", {})
        return ChatResponse(
            content=message.get("content", ""),
            model=data.get("model", request.model or self.default_model),
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatDelta]:
        request.stream = True
        try:
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
        except httpx.TimeoutException:
            raise LLMTimeoutError()
        except httpx.HTTPStatusError as exc:
            logger.error("LLM stream HTTP error: %s", exc.response.status_code)
            raise LLMError(f"llm returned {exc.response.status_code}")
        except httpx.HTTPError as exc:
            logger.error("LLM stream error: %s", exc)
            raise LLMError("llm service unavailable")
