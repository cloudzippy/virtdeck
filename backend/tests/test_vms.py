from collections.abc import Callable
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.libvirt.domains import DomainState, DomainSummary
from app.libvirt.exceptions import DomainNotFoundError, InvalidDomainStateError
from app.models.audit_log import AuditLog
from app.models.user import Role, User
from tests.conftest import get_token

SAMPLE = DomainSummary(
    uuid="11111111-1111-1111-1111-111111111111",
    name="test-vm",
    state=DomainState.SHUTOFF,
    vcpus=2,
    memory_kib=1048576,
    persistent=True,
)


def test_list_vms_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/vms")
    assert resp.status_code == 401


def test_list_vms(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="viewer@example.com", password="viewer-pass", role=Role.VIEWER)
    monkeypatch.setattr("app.libvirt.domains.list_domains", lambda: [SAMPLE])

    token = get_token(client, "viewer@example.com", "viewer-pass")
    resp = client.get("/api/vms", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "uuid": SAMPLE.uuid,
            "name": SAMPLE.name,
            "state": "shutoff",
            "vcpus": 2,
            "memory_kib": 1048576,
            "persistent": True,
        }
    ]


def test_viewer_cannot_start_vm(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="viewer@example.com", password="viewer-pass", role=Role.VIEWER)
    monkeypatch.setattr("app.libvirt.domains.start_domain", lambda uuid: SAMPLE)

    token = get_token(client, "viewer@example.com", "viewer-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/start", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403


def test_operator_can_start_vm(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)
    started = replace(SAMPLE, state=DomainState.RUNNING)
    monkeypatch.setattr("app.libvirt.domains.start_domain", lambda uuid: started)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/start", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["state"] == "running"


def test_start_vm_not_found(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)

    def _raise(uuid: str) -> DomainSummary:
        raise DomainNotFoundError(uuid)

    monkeypatch.setattr("app.libvirt.domains.start_domain", _raise)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/start", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 404


def test_only_admin_can_delete_vm(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)
    monkeypatch.setattr("app.libvirt.domains.delete_domain", lambda uuid: None)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.delete(f"/api/vms/{SAMPLE.uuid}", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403


@pytest.mark.parametrize("bad_uuid", ["not-a-uuid", "1111-2222", "test-vm"])
def test_invalid_vm_uuid_is_rejected_before_libvirt(
    client: TestClient,
    make_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
    bad_uuid: str,
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)

    def _fail(uuid: str) -> DomainSummary:
        raise AssertionError("libvirt layer must not be called with an invalid UUID")

    monkeypatch.setattr("app.libvirt.domains.start_domain", _fail)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(f"/api/vms/{bad_uuid}/start", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 422


def test_vm_uuid_is_normalised_to_lowercase(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="viewer@example.com", password="viewer-pass", role=Role.VIEWER)
    seen: list[str] = []

    def _get(uuid: str) -> DomainSummary:
        seen.append(uuid)
        return SAMPLE

    monkeypatch.setattr("app.libvirt.domains.get_domain", _get)

    token = get_token(client, "viewer@example.com", "viewer-pass")
    resp = client.get(
        f"/api/vms/{SAMPLE.uuid.upper()}", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert seen == [SAMPLE.uuid]


def test_reboot_shutoff_vm_returns_state(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)
    monkeypatch.setattr("app.libvirt.domains.reboot_domain", lambda uuid: SAMPLE)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/reboot", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["state"] == "shutoff"


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_viewer_cannot_pause_or_resume_vm(
    client: TestClient, make_user: Callable[..., User], action: str
) -> None:
    make_user(email="viewer@example.com", password="viewer-pass", role=Role.VIEWER)

    token = get_token(client, "viewer@example.com", "viewer-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/{action}", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 403


@pytest.mark.parametrize(
    ("action", "result_state"),
    [("pause", DomainState.PAUSED), ("resume", DomainState.RUNNING)],
)
def test_operator_can_pause_and_resume_vm(
    client: TestClient,
    make_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    action: str,
    result_state: DomainState,
) -> None:
    user = make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)
    monkeypatch.setattr(
        f"app.libvirt.domains.{action}_domain", lambda uuid: replace(SAMPLE, state=result_state)
    )

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/{action}", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["state"] == result_state
    entry = db_session.scalars(select(AuditLog)).one()
    assert (entry.user_id, entry.action, entry.vm_uuid) == (user.id, f"vm.{action}", SAMPLE.uuid)


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_pause_or_resume_shutoff_vm_is_conflict(
    client: TestClient,
    make_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
    action: str,
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)

    def _raise(uuid: str) -> DomainSummary:
        raise InvalidDomainStateError(uuid, DomainState.SHUTOFF, action)

    monkeypatch.setattr(f"app.libvirt.domains.{action}_domain", _raise)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/{action}", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 409
    assert "shutoff" in resp.json()["detail"]


def test_resume_vm_not_found(
    client: TestClient, make_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(email="op@example.com", password="operator-pass", role=Role.OPERATOR)

    def _raise(uuid: str) -> DomainSummary:
        raise DomainNotFoundError(uuid)

    monkeypatch.setattr("app.libvirt.domains.resume_domain", _raise)

    token = get_token(client, "op@example.com", "operator-pass")
    resp = client.post(
        f"/api/vms/{SAMPLE.uuid}/resume", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 404
