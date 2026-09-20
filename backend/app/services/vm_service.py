import asyncio
import logging

from sqlalchemy.orm import Session

from app.libvirt import domains as libvirt_domains
from app.libvirt.exceptions import DomainNotFoundError, LibvirtLayerError
from app.models.audit_log import AuditLog
from app.services.exceptions import VMNotFoundError, VMOperationError

logger = logging.getLogger(__name__)


def _audit(
    db: Session, user_id: str, action: str, vm_uuid: str | None, detail: str | None = None
) -> None:
    db.add(AuditLog(user_id=user_id, action=action, vm_uuid=vm_uuid, detail=detail))
    db.commit()


async def list_vms() -> list[libvirt_domains.DomainSummary]:
    try:
        return await asyncio.to_thread(libvirt_domains.list_domains)
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc


async def get_vm(uuid: str) -> libvirt_domains.DomainSummary:
    try:
        return await asyncio.to_thread(libvirt_domains.get_domain, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc


async def start_vm(db: Session, user_id: str, uuid: str) -> libvirt_domains.DomainSummary:
    try:
        summary = await asyncio.to_thread(libvirt_domains.start_domain, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    _audit(db, user_id, "vm.start", uuid)
    return summary


async def shutdown_vm(db: Session, user_id: str, uuid: str) -> libvirt_domains.DomainSummary:
    try:
        summary = await asyncio.to_thread(libvirt_domains.shutdown_domain, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    _audit(db, user_id, "vm.shutdown", uuid)
    return summary


async def force_stop_vm(db: Session, user_id: str, uuid: str) -> libvirt_domains.DomainSummary:
    try:
        summary = await asyncio.to_thread(libvirt_domains.force_stop_domain, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    _audit(db, user_id, "vm.force_stop", uuid)
    return summary


async def reboot_vm(db: Session, user_id: str, uuid: str) -> libvirt_domains.DomainSummary:
    try:
        summary = await asyncio.to_thread(libvirt_domains.reboot_domain, uuid)
    except DomainNotFoundError as exc:
        raise VMNotFoundError(uuid) from exc
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    _audit(db, user_id, "vm.reboot", uuid)
    return summary


async def delete_vm(db: Session, user_id: str, uuid: str) -> None:
    try:
        await asyncio.to_thread(libvirt_domains.delete_domain, uuid)
    except LibvirtLayerError as exc:
        raise VMOperationError(str(exc)) from exc
    _audit(db, user_id, "vm.delete", uuid)
