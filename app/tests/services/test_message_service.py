from __future__ import annotations

from app.schemas.message import MessageCreateRequest, MessagePayload
from app.schemas.session import SessionCreateRequest
from app.services.message_service import MessageService
from app.services.session_service import SessionService


def test_message_service_creates_message(db_session):
    session_service = SessionService(db_session)
    session_result = session_service.create_session(
        SessionCreateRequest(
            tenant_code="demo_tenant",
            channel="demo",
            external_user_id="u_10001",
        )
    )

    message_service = MessageService(db_session)
    result = message_service.create_message(
        MessageCreateRequest(
            tenant_code="demo_tenant",
            session_code=session_result.session_code,
            message=MessagePayload(type="text", content="你好"),
        )
    )

    assert result.message_code.startswith("m_")
    assert result.role == "user"
