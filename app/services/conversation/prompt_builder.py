from __future__ import annotations

from app.services.llm.base import ChatMessage

DEFAULT_SYSTEM_PROMPT = """你是一个专业的 AI 客服助手。请遵守以下规则：
1. 用中文回答用户问题，语气友好专业
2. 如果你不确定答案，请诚实告知，不要编造
3. 回答要简洁有条理
4. 涉及退款、赔付、法律等敏感问题时，建议用户联系人工客服"""


class PromptBuilder:
    def __init__(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def build(self, context_messages: list[ChatMessage]) -> list[ChatMessage]:
        """将 system prompt 与上下文拼装为完整消息列表"""
        return [
            ChatMessage(role="system", content=self.system_prompt),
            *context_messages,
        ]
