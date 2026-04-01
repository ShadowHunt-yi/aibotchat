from __future__ import annotations

import os
import sys
from pathlib import Path
from secrets import token_hex

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.session import create_engine_from_url, get_db
from app.core.config import get_settings


def _build_test_database_path() -> Path:
    base_dir = ROOT / ".pytest_tmp"
    base_dir.mkdir(exist_ok=True)
    return base_dir / f"test_{token_hex(4)}.db"


@pytest.fixture
def db_session():
    database_path = _build_test_database_path()
    engine = create_engine_from_url(f"sqlite:///{database_path}")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    db: Session = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
        if database_path.exists():
            database_path.unlink()


@pytest.fixture
def client():
    os.environ["APP_AUTO_CREATE_TABLES"] = "false"
    get_settings.cache_clear()

    database_path = _build_test_database_path()
    engine = create_engine_from_url(f"sqlite:///{database_path}")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    from app.main import app

    def override_get_db():
        db: Session = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()
    if database_path.exists():
        database_path.unlink()
    os.environ.pop("APP_AUTO_CREATE_TABLES", None)
    get_settings.cache_clear()
