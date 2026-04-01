from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.message import Message
from app.db.models.session import ChatSession


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_message(
        self,
        *,
        tenant_id: int,
        session_id: int,
        message_code: str,
        role: str,
        message_type: str,
        content: str | None,
        content_json: dict | None,
    ) -> Message:
        message = Message(
            tenant_id=tenant_id,
            session_id=session_id,
            message_code=message_code,
            role=role,
            message_type=message_type,
            content=content,
            content_json=content_json or {},
            status="accepted",
        )
        self.db.add(message)
        self.db.flush()
        return message

    def touch_session(self, chat_session: ChatSession, last_message_at: datetime) -> None:
        chat_session.last_message_at = last_message_at
        self.db.add(chat_session)
        self.db.flush()
