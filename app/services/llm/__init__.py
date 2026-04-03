from __future__ import annotations

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
