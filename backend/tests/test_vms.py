from collections.abc import Callable
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.libvirt.domains import DomainState, DomainSummary
from app.libvirt.exceptions import DomainNotFoundError
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
