from __future__ import annotations

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[int] = mapped_column(SmallInteger, default=1)

    channels = relationship("Channel", back_populates="tenant")
    users = relationship("User", back_populates="tenant")
    sessions = relationship("ChatSession", back_populates="tenant")
    messages = relationship("Message", back_populates="tenant")
