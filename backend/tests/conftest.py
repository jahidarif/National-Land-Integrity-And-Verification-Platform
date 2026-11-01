from __future__ import annotations

import os

# Ensure importing the application never requires a live PostgreSQL driver/server.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-secret-key-that-is-long-enough")
os.environ["MAIRA_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.domain.entities import Base
from app.infrastructure.database import get_db
from app.main import app
from app.presentation import chat_router


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """API test client backed by an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "max_upload_mb", 2)
    monkeypatch.setattr(settings, "chat_cache_ttl_seconds", 60)
    monkeypatch.setattr(settings, "maira_api_key", "")
    monkeypatch.setattr(settings, "maira_project_key", "")
    monkeypatch.setattr(settings, "maira_timeout_seconds", 4.0)
    chat_router._cache.clear()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.get("/api/auth/csrf")
        yield test_client

    app.dependency_overrides.clear()
    chat_router._cache.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def csrf(client) -> dict[str, str]:
    token = client.cookies.get("csrf_access_token", "")
    if not token:
        client.get("/api/auth/csrf")
        token = client.cookies.get("csrf_access_token", "")
    return {"X-CSRF-TOKEN": token}


def register_and_login(client, email="citizen@example.com", password="SafePass123!", role="User"):
    register = client.post(
        "/api/auth/register",
        json={"full_name": "Test Citizen", "email": email, "password": password, "role": role},
        headers=csrf(client),
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/auth/login", json={"email": email, "password": password}, headers=csrf(client))
    assert login.status_code == 200, login.text
    return login.json()


@pytest.fixture()
def authenticated_client(client):
    register_and_login(client)
    return client
