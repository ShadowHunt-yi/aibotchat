from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exception_handlers import NotFoundError
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.session_repo import SessionRepository
from app.schemas.message import MessageCreateRequest, MessageCreateResponse
from app.utils.ids import generate_message_code
from app.utils.time import utcnow


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.message_repo = MessageRepository(db)
        self.session_repo = SessionRepository(db)

    def create_message(self, payload: MessageCreateRequest) -> MessageCreateResponse:
        tenant = self.session_repo.get_tenant_by_code(payload.tenant_code)
        if tenant is None:
            raise NotFoundError("tenant not found")

        chat_session = self.session_repo.get_session_by_code(payload.session_code)
        if chat_session is None or chat_session.tenant_id != tenant.id:
            raise NotFoundError("session not found")

        message = self.message_repo.create_message(
            tenant_id=tenant.id,
            session_id=chat_session.id,
            message_code=generate_message_code(),
            role="user",
            message_type=payload.message.type,
            content=payload.message.content,
            content_json=payload.message.content_json,
        )
        self.message_repo.touch_session(chat_session, utcnow())
        self.db.commit()
        self.db.refresh(message)

        return MessageCreateResponse(
            message_code=message.message_code,
            role=message.role,
            status=message.status,
        )
