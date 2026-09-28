from uuid import UUID

from pydantic import BaseModel

from app.libvirt.domains import DomainState


class VMSummary(BaseModel):
    uuid: str
    name: str
    state: DomainState
    vcpus: int
    memory_kib: int
    persistent: bool
    owner_id: str | None


class VMOwnerUpdate(BaseModel):
    """Set a VM's owner, or clear it with `null` so the VM is unassigned (admin-only)."""

    owner_id: UUID | None
