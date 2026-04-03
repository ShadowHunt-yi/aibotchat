from __future__ import annotations

from app.db.repositories.message_repo import MessageRepository
from app.schemas.session import SessionCreateRequest
from app.services.conversation.context_manager import ContextManager
from app.services.session_service import SessionService
from app.utils.ids import generate_message_code
from app.utils.time import utcnow


def _setup_session(db_session):
    """创建一个 session 并返回 tenant, chat_session"""
    service = SessionService(db_session)
    result = service.create_session(
        SessionCreateRequest(
            tenant_code="demo_tenant",
            channel="demo",
            external_user_id="u_10001",
        )
    )

    from app.db.repositories.session_repo import SessionRepository

    repo = SessionRepository(db_session)
    tenant = repo.get_tenant_by_code("demo_tenant")
    chat_session = repo.get_session_by_code(result.session_code)
    return tenant, chat_session


def test_empty_context(db_session):
    tenant, chat_session = _setup_session(db_session)
    ctx = ContextManager(db_session)
    messages = ctx.build_context(chat_session.id)
    assert messages == []


def test_builds_context_from_messages(db_session):
    tenant, chat_session = _setup_session(db_session)
    msg_repo = MessageRepository(db_session)

    msg_repo.create_message(
        tenant_id=tenant.id,
        session_id=chat_session.id,
        message_code=generate_message_code(),
        role="user",
        message_type="text",
        content="你好",
        content_json=None,
    )
    msg_repo.create_message(
        tenant_id=tenant.id,
        session_id=chat_session.id,
        message_code=generate_message_code(),
        role="assistant",
        message_type="text",
        content="你好！",
        content_json=None,
    )
    db_session.commit()

    ctx = ContextManager(db_session)
    messages = ctx.build_context(chat_session.id)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "你好"
    assert messages[1].role == "assistant"
    assert messages[1].content == "你好！"


def test_respects_max_rounds(db_session):
    tenant, chat_session = _setup_session(db_session)
    msg_repo = MessageRepository(db_session)

    # 写入 6 条消息 (3 轮)
    for i in range(3):
        msg_repo.create_message(
            tenant_id=tenant.id,
            session_id=chat_session.id,
            message_code=generate_message_code(),
            role="user",
            message_type="text",
            content=f"问题{i}",
            content_json=None,
        )
        msg_repo.create_message(
            tenant_id=tenant.id,
            session_id=chat_session.id,
            message_code=generate_message_code(),
            role="assistant",
            message_type="text",
            content=f"回答{i}",
            content_json=None,
        )
    db_session.commit()

    # max_rounds=1 只保留最后 2 条
    ctx = ContextManager(db_session, max_rounds=1)
    messages = ctx.build_context(chat_session.id)

    assert len(messages) == 2
    assert messages[0].content == "问题2"
    assert messages[1].content == "回答2"
