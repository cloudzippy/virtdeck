from pydantic import BaseModel

from app.libvirt.domains import DomainState


class VMSummary(BaseModel):
    uuid: str
    name: str
    state: DomainState
    vcpus: int
    memory_kib: int
    persistent: bool
