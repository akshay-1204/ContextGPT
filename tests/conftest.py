"""Pytest fixtures and configuration for ContextGPT test suite."""

import os
import sys
import pytest
from typing import Generator

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment flags
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-automated-pytest-execution-32c"

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.services.auth_service import AuthService
from backend.app.schemas.user import UserRegister

# Create in-memory SQLite engine for fast, isolated tests
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides a clean, isolated database session per test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient configured with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session):
    """Creates a primary test user and returns Authorization headers."""
    register_payload = {
        "name": "Alice Tester",
        "email": "alice@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }
    client.post("/api/v1/auth/register", json=register_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]
    refresh = login_res.json()["refresh_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "token": token,
        "refresh_token": refresh,
        "email": "alice@example.com",
    }


@pytest.fixture
def second_user_headers(client: TestClient):
    """Creates a second distinct user to test multi-tenant resource isolation."""
    register_payload = {
        "name": "Bob Intruder",
        "email": "bob@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }
    client.post("/api/v1/auth/register", json=register_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": "bob@example.com", "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "email": "bob@example.com",
    }
