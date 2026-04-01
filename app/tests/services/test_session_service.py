from __future__ import annotations

from app.schemas.session import SessionCreateRequest
from app.services.session_service import SessionService


def test_session_service_creates_session(db_session):
    service = SessionService(db_session)

    result = service.create_session(
        SessionCreateRequest(
            tenant_code="demo_tenant",
            channel="demo",
            external_user_id="u_10001",
        )
    )

    assert result.session_code.startswith("s_")
    assert result.status == "active"
