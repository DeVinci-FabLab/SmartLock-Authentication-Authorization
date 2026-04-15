# tests/conftest.py
import os
import sys
from pathlib import Path

# Must precede all src imports so settings loads with test values
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("KEYCLOAK_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "smartlock")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "smartlock-api")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.keycloak import (
    require_admin,
    require_codir,
    require_codir_or_admin,
    require_locker_client,
    require_materialiste_or_above,
    require_nfc_scanner,
    validate_jwt,
)
from src.database.base import Base
from src.database.session import get_db
from src.main import app, limiter

# Disable rate limiting globally for all tests
limiter.enabled = False

# Single in-memory engine shared across the session
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# DB fixture: each test gets its own transaction, rolled back at teardown
# ---------------------------------------------------------------------------
@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Pre-defined JWT payloads
# ---------------------------------------------------------------------------
ADMIN_PAYLOAD = {
    "sub": "admin-123",
    "realm_access": {"roles": ["admin", "membre"]},
}
CODIR_PAYLOAD = {
    "sub": "codir-456",
    "realm_access": {"roles": ["membre", "codir"]},
}
MATERIALISTE_PAYLOAD = {
    "sub": "materialiste-789",
    "realm_access": {"roles": ["membre", "materialiste"]},
}
MEMBRE_PAYLOAD = {
    "sub": "membre-000",
    "realm_access": {"roles": ["membre"]},
}
NFC_PAYLOAD = {"azp": "nfc-scanner"}
RPI_PAYLOAD = {"azp": "smartlock-lockers"}


# ---------------------------------------------------------------------------
# Client factory: yields a TestClient with the given dependency overrides.
# Clears all overrides at teardown to prevent inter-test bleed.
# ---------------------------------------------------------------------------
def _make_client(db_session, extra_overrides: dict):
    def override_get_db():
        yield db_session

    overrides = {get_db: override_get_db, **extra_overrides}
    app.dependency_overrides.update(overrides)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db):
    """Unauthenticated client (only DB overridden)."""
    yield from _make_client(db, {})


@pytest.fixture()
def admin_client(db):
    p = ADMIN_PAYLOAD
    yield from _make_client(db, {
        validate_jwt: lambda: p,
        require_admin: lambda: p,
        require_codir_or_admin: lambda: p,
        require_materialiste_or_above: lambda: p,
    })


@pytest.fixture()
def codir_client(db):
    p = CODIR_PAYLOAD
    yield from _make_client(db, {
        validate_jwt: lambda: p,
        require_codir: lambda: p,
        require_codir_or_admin: lambda: p,
        require_materialiste_or_above: lambda: p,
    })


@pytest.fixture()
def materialiste_client(db):
    p = MATERIALISTE_PAYLOAD
    yield from _make_client(db, {
        validate_jwt: lambda: p,
        require_materialiste_or_above: lambda: p,
    })


@pytest.fixture()
def membre_client(db):
    p = MEMBRE_PAYLOAD
    yield from _make_client(db, {
        validate_jwt: lambda: p,
    })


@pytest.fixture()
def nfc_client(db):
    yield from _make_client(db, {
        require_nfc_scanner: lambda: NFC_PAYLOAD,
    })


@pytest.fixture()
def rpi_client(db):
    yield from _make_client(db, {
        require_locker_client: lambda: RPI_PAYLOAD,
    })
