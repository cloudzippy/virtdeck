import importlib.util
import os
import sys
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

_TEST_DB_PATH = Path(__file__).parent / "test_virtdeck.db"
os.environ.setdefault("VIRTDECK_DATABASE_URL", f"sqlite:///{_TEST_DB_PATH}")
os.environ.setdefault("VIRTDECK_SECRET_KEY", "test-only-secret-key-at-least-32-bytes-long")
os.environ.setdefault("VIRTDECK_LIBVIRT_URI", "test:///default")


def _ensure_libvirt_importable() -> bool:
    """Fall back to a stub `libvirt` module if the real bindings aren't installed.

    Returns True if the stub was installed (i.e. no real libvirt-python present).
    """
    if importlib.util.find_spec("libvirt") is not None:
        return False
    from tests.fakes import stub_libvirt

    sys.modules["libvirt"] = stub_libvirt
    return True


LIBVIRT_IS_STUBBED = _ensure_libvirt_importable()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import Role, User  # noqa: E402
from app.services.auth_service import create_user  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(db_session: Session) -> Callable[..., User]:
    def _make(
        email: str = "user@example.com",
        password: str = "correct horse battery staple",
        role: Role = Role.VIEWER,
    ) -> User:
        return create_user(db_session, email=email, password=password, role=role)

    return _make


def get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    token: str = resp.json()["access_token"]
    return token
