from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exception_handlers import NotFoundError
from app.db.repositories.message_repo import MessageRepository
from app.db.repositories.session_repo import SessionRepository
from app.db.session import get_db
from app.schemas.common import APIResponse, success_response
from app.schemas.history import HistoryMessage, HistoryResponse

router = APIRouter(prefix="/sessions", tags=["history"])


@router.get(
    "/{session_code}/messages",
    response_model=APIResponse[HistoryResponse],
)
def get_session_messages(
    session_code: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[HistoryResponse]:
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)

    chat_session = session_repo.get_session_by_code(session_code)
    if chat_session is None:
        raise NotFoundError("session not found")

    items, total = message_repo.list_messages(
        chat_session.id, limit=limit, offset=offset,
    )

    return success_response(
        HistoryResponse(
            session_code=session_code,
            items=[
                HistoryMessage(
                    message_code=m.message_code,
                    role=m.role,
                    content=m.content,
                    status=m.status,
                    created_at=m.created_at,
                )
                for m in items
            ],
            total=total,
        )
    )
