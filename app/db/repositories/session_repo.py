from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.session import ChatSession
from app.db.models.tenant import Tenant
from app.db.models.user import User


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_tenant_by_code(self, tenant_code: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.tenant_code == tenant_code).one_or_none()

    def create_tenant(self, tenant_code: str, name: str) -> Tenant:
        tenant = Tenant(tenant_code=tenant_code, name=name)
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def get_channel_by_code(self, tenant_id: int, channel_code: str) -> Channel | None:
        return (
            self.db.query(Channel)
            .filter(Channel.tenant_id == tenant_id, Channel.channel_code == channel_code)
            .one_or_none()
        )

    def create_channel(self, tenant_id: int, channel_code: str, channel_type: str) -> Channel:
        channel = Channel(tenant_id=tenant_id, channel_code=channel_code, channel_type=channel_type)
        self.db.add(channel)
        self.db.flush()
        return channel

    def get_user_by_external_id(self, tenant_id: int, external_user_id: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.tenant_id == tenant_id, User.external_user_id == external_user_id)
            .one_or_none()
        )

    def create_user(self, tenant_id: int, external_user_id: str) -> User:
        user = User(tenant_id=tenant_id, external_user_id=external_user_id)
        self.db.add(user)
        self.db.flush()
        return user

    def create_session(
        self,
        *,
        tenant_id: int,
        channel_id: int,
        user_id: int,
        session_code: str,
        extra: dict | None,
    ) -> ChatSession:
        chat_session = ChatSession(
            tenant_id=tenant_id,
            channel_id=channel_id,
            user_id=user_id,
            session_code=session_code,
            status="active",
            extra=extra or {},
        )
        self.db.add(chat_session)
        self.db.flush()
        return chat_session

    def get_session_by_code(self, session_code: str) -> ChatSession | None:
        return self.db.query(ChatSession).filter(ChatSession.session_code == session_code).one_or_none()
