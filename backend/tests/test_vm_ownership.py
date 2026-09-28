from collections.abc import Callable
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.libvirt.domains import DomainState, DomainSummary
from app.libvirt.exceptions import DomainNotFoundError
from app.models.audit_log import AuditLog
from app.models.user import Role, User
from app.models.vm_ownership import VMOwnership
from tests.conftest import get_token

OWNED = DomainSummary(
    uuid="11111111-1111-1111-1111-111111111111",
    name="owned-vm",
    state=DomainState.SHUTOFF,
    vcpus=2,
    memory_kib=1048576,
    persistent=True,
)
OTHERS = replace(OWNED, uuid="22222222-2222-2222-2222-222222222222", name="others-vm")
UNASSIGNED = replace(OWNED, uuid="33333333-3333-3333-3333-333333333333", name="unassigned-vm")
MISSING_UUID = "44444444-4444-4444-4444-444444444444"
ALL = {d.uuid: d for d in (OWNED, OTHERS, UNASSIGNED)}


def _own(db: Session, vm_uuid: str, owner: User) -> None:
    db.add(VMOwnership(vm_uuid=vm_uuid, owner_id=owner.id, assigned_by=owner.id))
    db.commit()


def _auth(client: TestClient, user: User, password: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_token(client, user.email, password)}"}


def _get_domain(uuid: str) -> DomainSummary:
    if uuid not in ALL:
        raise DomainNotFoundError(uuid)
    return ALL[uuid]


@pytest.fixture
def libvirt_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Fake the libvirt layer over three VMs and record every lifecycle call made to it."""
    calls: list[tuple[str, str]] = []

    def _recorder(name: str) -> Callable[[str], DomainSummary]:
        def _op(uuid: str) -> DomainSummary:
            calls.append((name, uuid))
            return _get_domain(uuid)

        return _op

    monkeypatch.setattr("app.libvirt.domains.list_domains", lambda: list(ALL.values()))
    monkeypatch.setattr("app.libvirt.domains.get_domain", _get_domain)
    for name in ("start", "shutdown", "force_stop", "reboot", "pause", "resume"):
        monkeypatch.setattr(f"app.libvirt.domains.{name}_domain", _recorder(name))
    monkeypatch.setattr(
        "app.libvirt.domains.delete_domain", lambda uuid: calls.append(("delete", uuid))
    )
    return calls


@pytest.fixture
def users(make_user: Callable[..., User], db_session: Session) -> dict[str, User]:
    """An admin, an operator who owns OWNED, and a viewer who owns OTHERS."""
    admin = make_user(email="admin@example.com", password="admin-pass", role=Role.ADMIN)
    operator = make_user(email="op@example.com", password="op-pass", role=Role.OPERATOR)
    viewer = make_user(email="viewer@example.com", password="viewer-pass", role=Role.VIEWER)
    _own(db_session, OWNED.uuid, operator)
    _own(db_session, OTHERS.uuid, viewer)
    return {"admin": admin, "operator": operator, "viewer": viewer}


PASSWORDS = {"admin": "admin-pass", "operator": "op-pass", "viewer": "viewer-pass"}


def _as(client: TestClient, users: dict[str, User], who: str) -> dict[str, str]:
    return _auth(client, users[who], PASSWORDS[who])


# --- Visibility -------------------------------------------------------------------------------


def test_admin_sees_every_vm_including_unassigned(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.get("/api/vms", headers=_as(client, users, "admin"))

    assert resp.status_code == 200
    owners = {vm["name"]: vm["owner_id"] for vm in resp.json()}
    assert owners == {
        "owned-vm": users["operator"].id,
        "others-vm": users["viewer"].id,
        "unassigned-vm": None,
    }


@pytest.mark.parametrize(("who", "visible"), [("operator", "owned-vm"), ("viewer", "others-vm")])
def test_non_admins_see_only_their_own_vms(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    who: str,
    visible: str,
) -> None:
    resp = client.get("/api/vms", headers=_as(client, users, who))

    assert resp.status_code == 200
    assert [vm["name"] for vm in resp.json()] == [visible]


@pytest.mark.parametrize("vm_uuid", [OTHERS.uuid, UNASSIGNED.uuid])
def test_get_vm_the_user_does_not_own_is_not_found(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    vm_uuid: str,
) -> None:
    resp = client.get(f"/api/vms/{vm_uuid}", headers=_as(client, users, "operator"))

    assert resp.status_code == 404


def test_hidden_and_missing_vms_are_indistinguishable(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    headers = _as(client, users, "operator")

    hidden = client.get(f"/api/vms/{OTHERS.uuid}", headers=headers)
    missing = client.get(f"/api/vms/{MISSING_UUID}", headers=headers)

    assert hidden.status_code == missing.status_code == 404
    assert hidden.json()["detail"].replace(OTHERS.uuid, "X") == missing.json()["detail"].replace(
        MISSING_UUID, "X"
    )


# --- Lifecycle actions ------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["start", "shutdown", "force-stop", "reboot", "pause", "resume"])
@pytest.mark.parametrize("vm_uuid", [OTHERS.uuid, UNASSIGNED.uuid])
def test_operator_cannot_act_on_vms_they_do_not_own(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
    action: str,
    vm_uuid: str,
) -> None:
    resp = client.post(f"/api/vms/{vm_uuid}/{action}", headers=_as(client, users, "operator"))

    assert resp.status_code == 404
    assert libvirt_calls == []
    assert db_session.scalars(select(AuditLog)).all() == []


def test_operator_can_act_on_their_own_vm(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.post(f"/api/vms/{OWNED.uuid}/start", headers=_as(client, users, "operator"))

    assert resp.status_code == 200
    assert resp.json()["owner_id"] == users["operator"].id
    assert libvirt_calls == [("start", OWNED.uuid)]


def test_owning_a_vm_does_not_let_a_viewer_operate_it(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.post(f"/api/vms/{OTHERS.uuid}/start", headers=_as(client, users, "viewer"))

    assert resp.status_code == 403
    assert libvirt_calls == []


def test_admin_can_act_on_unassigned_vm(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.post(f"/api/vms/{UNASSIGNED.uuid}/start", headers=_as(client, users, "admin"))

    assert resp.status_code == 200
    assert resp.json()["owner_id"] is None
    assert libvirt_calls == [("start", UNASSIGNED.uuid)]


def test_deleting_a_vm_removes_its_ownership(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
) -> None:
    resp = client.delete(f"/api/vms/{OWNED.uuid}", headers=_as(client, users, "admin"))

    assert resp.status_code == 204
    assert libvirt_calls == [("delete", OWNED.uuid)]
    assert db_session.get(VMOwnership, OWNED.uuid) is None


# --- Assigning owners -------------------------------------------------------------------------


def test_admin_assigns_owner_and_the_owner_gains_access(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
) -> None:
    operator = users["operator"]

    resp = client.put(
        f"/api/vms/{UNASSIGNED.uuid}/owner",
        json={"owner_id": operator.id},
        headers=_as(client, users, "admin"),
    )

    assert resp.status_code == 200
    assert resp.json()["owner_id"] == operator.id
    ownership = db_session.get(VMOwnership, UNASSIGNED.uuid)
    assert ownership is not None
    assert ownership.assigned_by == users["admin"].id
    entry = db_session.scalars(select(AuditLog)).one()
    assert (entry.user_id, entry.action, entry.vm_uuid, entry.detail) == (
        users["admin"].id,
        "vm.assign_owner",
        UNASSIGNED.uuid,
        f"owner={operator.id}",
    )
    start = client.post(f"/api/vms/{UNASSIGNED.uuid}/start", headers=_as(client, users, "operator"))
    assert start.status_code == 200


def test_reassigning_replaces_the_previous_owner(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.put(
        f"/api/vms/{OWNED.uuid}/owner",
        json={"owner_id": users["viewer"].id},
        headers=_as(client, users, "admin"),
    )

    assert resp.status_code == 200
    listing = client.get("/api/vms", headers=_as(client, users, "operator"))
    assert listing.json() == []


def test_clearing_the_owner_makes_the_vm_unassigned(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
) -> None:
    resp = client.put(
        f"/api/vms/{OWNED.uuid}/owner", json={"owner_id": None}, headers=_as(client, users, "admin")
    )

    assert resp.status_code == 200
    assert resp.json()["owner_id"] is None
    assert db_session.get(VMOwnership, OWNED.uuid) is None
    entry = db_session.scalars(select(AuditLog)).one()
    assert entry.detail == "owner=none"


@pytest.mark.parametrize("who", ["operator", "viewer"])
def test_only_admins_can_assign_owners(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
    who: str,
) -> None:
    # Even the current owner may not hand the VM to someone else.
    resp = client.put(
        f"/api/vms/{OWNED.uuid}/owner",
        json={"owner_id": users["viewer"].id},
        headers=_as(client, users, who),
    )

    assert resp.status_code == 403
    ownership = db_session.get(VMOwnership, OWNED.uuid)
    assert ownership is not None
    assert ownership.owner_id == users["operator"].id


def test_assigning_an_unknown_user_is_rejected(
    client: TestClient, users: dict[str, User], libvirt_calls: list[tuple[str, str]]
) -> None:
    resp = client.put(
        f"/api/vms/{UNASSIGNED.uuid}/owner",
        json={"owner_id": MISSING_UUID},
        headers=_as(client, users, "admin"),
    )

    assert resp.status_code == 422


def test_assigning_an_inactive_user_is_rejected(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
) -> None:
    viewer = db_session.get(User, users["viewer"].id)
    assert viewer is not None
    viewer.is_active = False
    db_session.commit()

    resp = client.put(
        f"/api/vms/{UNASSIGNED.uuid}/owner",
        json={"owner_id": viewer.id},
        headers=_as(client, users, "admin"),
    )

    assert resp.status_code == 422
    assert db_session.get(VMOwnership, UNASSIGNED.uuid) is None


@pytest.mark.parametrize("body", [{"owner_id": "not-a-uuid"}, {}])
def test_malformed_owner_payload_is_rejected(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    body: dict[str, str],
) -> None:
    resp = client.put(
        f"/api/vms/{UNASSIGNED.uuid}/owner", json=body, headers=_as(client, users, "admin")
    )

    assert resp.status_code == 422


def test_assigning_owner_of_missing_vm_is_not_found(
    client: TestClient,
    users: dict[str, User],
    libvirt_calls: list[tuple[str, str]],
    db_session: Session,
) -> None:
    resp = client.put(
        f"/api/vms/{MISSING_UUID}/owner",
        json={"owner_id": users["operator"].id},
        headers=_as(client, users, "admin"),
    )

    assert resp.status_code == 404
    assert db_session.get(VMOwnership, MISSING_UUID) is None
