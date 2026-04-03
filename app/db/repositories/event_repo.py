from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.message_event import MessageEvent


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._seq_cache: dict[int, int] = {}

    def _next_seq(self, session_id: int) -> int:
        if session_id not in self._seq_cache:
            last = (
                self.db.query(MessageEvent)
                .filter(MessageEvent.session_id == session_id)
                .order_by(MessageEvent.event_seq.desc())
                .first()
            )
            self._seq_cache[session_id] = last.event_seq if last else 0
        self._seq_cache[session_id] += 1
        return self._seq_cache[session_id]

    def create_event(
        self,
        *,
        tenant_id: int,
        session_id: int,
        message_id: int | None,
        event_type: str,
        payload: dict,
    ) -> MessageEvent:
        event = MessageEvent(
            tenant_id=tenant_id,
            session_id=session_id,
            message_id=message_id,
            event_type=event_type,
            event_seq=self._next_seq(session_id),
            payload=payload,
        )
        self.db.add(event)
        self.db.flush()
        return event
