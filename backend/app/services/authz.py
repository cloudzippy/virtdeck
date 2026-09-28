"""Per-VM authorization: who may see or act on which VM.

Rules (see docs/architecture.md, "Auth and RBAC"):
- Admins see and act on every VM, including unassigned ones.
- Everyone else sees only the VMs they own. What they may *do* to those VMs is still limited
  by their role, which the API layer checks with `require_role`.
- A VM the actor may not see is reported as not found, so its existence isn't disclosed.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Role
from app.models.vm_ownership import VMOwnership
from app.services.exceptions import VMNotFoundError


@dataclass(frozen=True)
class Actor:
    """The authenticated user a service call is made on behalf of."""

    id: str
    role: Role

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


def owner_of(db: Session, vm_uuid: str) -> str | None:
    return db.scalar(select(VMOwnership.owner_id).where(VMOwnership.vm_uuid == vm_uuid))


def owners_by_vm(db: Session) -> dict[str, str]:
    rows = db.execute(select(VMOwnership.vm_uuid, VMOwnership.owner_id))
    return {vm_uuid: owner_id for vm_uuid, owner_id in rows}


def can_see(actor: Actor, owner_id: str | None) -> bool:
    return actor.is_admin or (owner_id is not None and owner_id == actor.id)


def authorize_vm(db: Session, actor: Actor, vm_uuid: str) -> str | None:
    """Return the VM's owner ID, or raise VMNotFoundError if the actor may not see it."""
    owner_id = owner_of(db, vm_uuid)
    if not can_see(actor, owner_id):
        raise VMNotFoundError(vm_uuid)
    return owner_id
