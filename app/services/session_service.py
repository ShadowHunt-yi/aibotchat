from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.session_repo import SessionRepository
from app.schemas.session import SessionCreateRequest, SessionCreateResponse
from app.utils.ids import generate_session_code


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.session_repo = SessionRepository(db)

    def create_session(self, payload: SessionCreateRequest) -> SessionCreateResponse:
        tenant = self.session_repo.get_tenant_by_code(payload.tenant_code)
        if tenant is None:
            tenant = self.session_repo.create_tenant(
                tenant_code=payload.tenant_code,
                name=payload.tenant_code,
            )

        channel = self.session_repo.get_channel_by_code(tenant.id, payload.channel)
        if channel is None:
            channel = self.session_repo.create_channel(
                tenant_id=tenant.id,
                channel_code=payload.channel,
                channel_type=payload.channel,
            )

        user = self.session_repo.get_user_by_external_id(tenant.id, payload.external_user_id)
        if user is None:
            user = self.session_repo.create_user(
                tenant_id=tenant.id,
                external_user_id=payload.external_user_id,
            )

        chat_session = self.session_repo.create_session(
            tenant_id=tenant.id,
            channel_id=channel.id,
            user_id=user.id,
            session_code=generate_session_code(),
            extra=payload.metadata,
        )
        self.db.commit()
        self.db.refresh(chat_session)

        return SessionCreateResponse(
            session_code=chat_session.session_code,
            status=chat_session.status,
            created_at=chat_session.created_at,
        )
