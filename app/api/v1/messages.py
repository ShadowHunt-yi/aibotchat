from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import APIResponse, success_response
from app.schemas.message import MessageCreateRequest, MessageCreateResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=APIResponse[MessageCreateResponse], status_code=status.HTTP_202_ACCEPTED)
def create_message(
    payload: MessageCreateRequest,
    db: Session = Depends(get_db),
) -> APIResponse[MessageCreateResponse]:
    service = MessageService(db)
    return success_response(service.create_message(payload))
