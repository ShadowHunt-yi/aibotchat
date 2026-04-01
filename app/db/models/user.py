from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "external_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    external_user_id: Mapped[str] = mapped_column(String(128))
    nickname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone_masked: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    sessions = relationship("ChatSession", back_populates="user")
