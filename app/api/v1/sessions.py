from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import APIResponse, success_response
from app.schemas.session import SessionCreateRequest, SessionCreateResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=APIResponse[SessionCreateResponse], status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
) -> APIResponse[SessionCreateResponse]:
    service = SessionService(db)
    return success_response(service.create_session(payload))
