from __future__ import annotations

from app.db.repositories.event_repo import EventRepository
from app.schemas.session import SessionCreateRequest
from app.services.session_service import SessionService


def _setup(db_session):
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
    session = repo.get_session_by_code(result.session_code)
    return tenant, session


def test_create_event_increments_seq(db_session):
    tenant, chat_session = _setup(db_session)
    event_repo = EventRepository(db_session)

    e1 = event_repo.create_event(
        tenant_id=tenant.id,
        session_id=chat_session.id,
        message_id=None,
        event_type="llm_started",
        payload={"model": "gpt-4o-mini"},
    )
    e2 = event_repo.create_event(
        tenant_id=tenant.id,
        session_id=chat_session.id,
        message_id=None,
        event_type="llm_finished",
        payload={"finish_reason": "stop"},
    )
    db_session.commit()

    assert e1.event_seq == 1
    assert e2.event_seq == 2
    assert e1.event_type == "llm_started"
    assert e2.event_type == "llm_finished"
