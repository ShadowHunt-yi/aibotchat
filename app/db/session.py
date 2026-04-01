from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import channel, message, message_event, session, tenant, user  # noqa: F401


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_connect_args(database_url),
    )


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine_from_url(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


settings = get_settings()
engine = create_engine_from_url(settings.resolved_database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
