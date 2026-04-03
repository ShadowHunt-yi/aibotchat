from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.message import Message
from app.services.llm.base import ChatMessage


class ContextManager:
    def __init__(self, db: Session, max_rounds: int = 20) -> None:
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
            messages = messages[-(self.max_rounds * 2) :]

        return [ChatMessage(role=m.role, content=m.content or "") for m in messages]
