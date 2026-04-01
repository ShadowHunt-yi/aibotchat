from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Channel(TimestampMixin, Base):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("tenant_id", "channel_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    channel_code: Mapped[str] = mapped_column(String(64))
    channel_type: Mapped[str] = mapped_column(String(32))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)

    tenant = relationship("Tenant", back_populates="channels")
    sessions = relationship("ChatSession", back_populates="channel")
