import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.libvirt import domains as libvirt_domains
from app.libvirt.exceptions import (
    DomainNotFoundError,
    InvalidDomainStateError,
    LibvirtLayerError,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.vm_ownership import VMOwnership
from app.services.authz import Actor, authorize_vm, can_see, owners_by_vm
from app.services.exceptions import (
    InvalidOwnerError,
    VMNotFoundError,
    VMOperationError,
    VMStateConflictError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VMView:
    """A VM's live libvirt state plus the ownership VirtDeck records for it."""

    summary: libvirt_domains.DomainSummary
    owner_id: str | None


def _audit(
    db: Session, user_id: str, action: str, vm_uuid: str | None, detail: str | None = None
) -> None:
    db.add(AuditLog(user_id=user_id, action=action, vm_uuid=vm_uuid, detail=detail))
    db.commit()


async def _call_libvirt(
    operation: Callable[[str], libvirt_domains.DomainSummary], uuid: str
) -> libvirt_domains.DomainSummary:
    try:
        return await asyncio.to_thread(operation, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except InvalidDomainStateError as exc:
        raise VMStateConflictError(str(exc)) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc


async def _lifecycle(
    db: Session,
    actor: Actor,
    uuid: str,
    operation: Callable[[str], libvirt_domains.DomainSummary],
    action: str,
) -> VMView:
    # Ownership lives in our database, so check it before touching the hypervisor.
    owner_id = authorize_vm(db, actor, uuid)
    summary = await _call_libvirt(operation, uuid)
    _audit(db, actor.id, action, uuid)
    return VMView(summary, owner_id)


async def list_vms(db: Session, actor: Actor) -> list[VMView]:
    try:
        summaries = await asyncio.to_thread(libvirt_domains.list_domains)
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    owners = owners_by_vm(db)
    views = (VMView(s, owners.get(s.uuid)) for s in summaries)
    return [v for v in views if can_see(actor, v.owner_id)]


async def get_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    owner_id = authorize_vm(db, actor, uuid)
    summary = await _call_libvirt(libvirt_domains.get_domain, uuid)
    return VMView(summary, owner_id)


async def start_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.start_domain, "vm.start")


async def shutdown_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.shutdown_domain, "vm.shutdown")


async def force_stop_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.force_stop_domain, "vm.force_stop")


async def reboot_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.reboot_domain, "vm.reboot")


async def pause_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.pause_domain, "vm.pause")


async def resume_vm(db: Session, actor: Actor, uuid: str) -> VMView:
    return await _lifecycle(db, actor, uuid, libvirt_domains.resume_domain, "vm.resume")


async def delete_vm(db: Session, actor: Actor, uuid: str) -> None:
    authorize_vm(db, actor, uuid)
    try:
        await asyncio.to_thread(libvirt_domains.delete_domain, uuid)
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    db.execute(delete(VMOwnership).where(VMOwnership.vm_uuid == uuid))
    _audit(db, actor.id, "vm.delete", uuid)


async def assign_owner(db: Session, actor: Actor, uuid: str, owner_id: str | None) -> VMView:
    """Set or clear a VM's owner. Callers must restrict this to admins."""
    summary = await _call_libvirt(libvirt_domains.get_domain, uuid)
    if owner_id is not None:
        owner = db.scalar(select(User).where(User.id == owner_id))
        if owner is None or not owner.is_active:
            raise InvalidOwnerError(f"no active user with id {owner_id}")
    db.execute(delete(VMOwnership).where(VMOwnership.vm_uuid == uuid))
    if owner_id is not None:
        db.add(VMOwnership(vm_uuid=uuid, owner_id=owner_id, assigned_by=actor.id))
    _audit(db, actor.id, "vm.assign_owner", uuid, detail=f"owner={owner_id or 'none'}")
    logger.info("vm_uuid=%s owner set to %s by user_id=%s", uuid, owner_id, actor.id)
    return VMView(summary, owner_id)
