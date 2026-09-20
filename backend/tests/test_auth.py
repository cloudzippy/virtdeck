from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import Role, User


def test_login_success(client: TestClient, make_user: Callable[..., User]) -> None:
    make_user(email="admin@example.com", password="s3cret-pass", role=Role.ADMIN)

    resp = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "s3cret-pass"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client: TestClient, make_user: Callable[..., User]) -> None:
    make_user(email="admin@example.com", password="s3cret-pass")

    resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})

    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"email": "nope@example.com", "password": "x"})

    assert resp.status_code == 401
