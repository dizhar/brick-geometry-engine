"""
Shared fixtures for API tests.

Uses an in-memory SQLite database (via StaticPool so all connections share the
same in-memory state) instead of PostgreSQL, making tests dependency-free.

DATABASE_URL must be set *before* api.database is first imported so that
module-level code in database.py does not raise KeyError.
"""

import os

# Set before any api.* import — prevents database.py from crashing on
# os.environ["DATABASE_URL"] when no real PostgreSQL is available.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import api.database as _db_module
import api.main as _main_module
from api.database import Base, get_db
from api.main import app

# ---------------------------------------------------------------------------
# One shared SQLite engine for the whole test session.
# StaticPool ensures every connection reuse the same underlying connection,
# so the in-memory database is visible across sessions.
# ---------------------------------------------------------------------------
_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)

# Patch the module globals so the lifespan's Base.metadata.create_all(engine)
# and any direct engine usage also target our SQLite engine.
# api.main imports `engine` by name so we must patch its module namespace too.
_db_module.engine = _TEST_ENGINE
_db_module.SessionLocal = _TestingSession
_main_module.engine = _TEST_ENGINE


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    """
    Yield a FastAPI TestClient backed by a fresh in-memory SQLite database.

    Tables are created before the test and dropped afterwards so each test
    starts with a clean slate.
    """
    Base.metadata.create_all(bind=_TEST_ENGINE)
    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_TEST_ENGINE)
