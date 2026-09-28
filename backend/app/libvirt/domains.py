"""Domain (VM) operations against libvirt. All calls here are blocking."""

import enum
from dataclasses import dataclass

import libvirt

from app.libvirt.connection import get_connection
from app.libvirt.exceptions import (
    DomainNotFoundError,
    InvalidDomainStateError,
    LibvirtLayerError,
)

_STATE_MAP = {
    libvirt.VIR_DOMAIN_NOSTATE: "unknown",
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "blocked",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "shutting_down",
    libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_PMSUSPENDED: "suspended",
}


class DomainState(enum.StrEnum):
    UNKNOWN = "unknown"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    SHUTOFF = "shutoff"
    CRASHED = "crashed"
    SUSPENDED = "suspended"


# "blocked" means running but waiting on I/O, so libvirt treats it like running.
_PAUSABLE_STATES = frozenset({DomainState.RUNNING, DomainState.BLOCKED})


@dataclass(frozen=True)
class DomainSummary:
    uuid: str
    name: str
    state: DomainState
    vcpus: int
    memory_kib: int
    persistent: bool


def _to_state(raw_state: int) -> DomainState:
    return DomainState(_STATE_MAP.get(raw_state, "unknown"))


def _lookup(uuid: str) -> libvirt.virDomain:
    conn = get_connection()
    try:
        return conn.lookupByUUIDString(uuid)
    except libvirt.libvirtError as exc:
        raise DomainNotFoundError(uuid) from exc


def _summarize(domain: libvirt.virDomain) -> DomainSummary:
    try:
        raw_state, _reason = domain.state()
        info = domain.info()  # [state, maxMem, memory, nrVirtCpu, cpuTime]
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to read domain state: {exc}") from exc
    return DomainSummary(
        uuid=domain.UUIDString(),
        name=domain.name(),
        state=_to_state(raw_state),
        vcpus=info[3],
        memory_kib=info[2],
        persistent=bool(domain.isPersistent()),
    )


def list_domains() -> list[DomainSummary]:
    conn = get_connection()
    try:
        domains = conn.listAllDomains()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to list domains: {exc}") from exc
    return [_summarize(d) for d in domains]


def get_domain(uuid: str) -> DomainSummary:
    return _summarize(_lookup(uuid))


def start_domain(uuid: str) -> DomainSummary:
    """Start a domain. Idempotent: already-running is not an error."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state == DomainState.RUNNING:
        return summary
    try:
        domain.create()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to start domain {uuid}: {exc}") from exc
    return _summarize(domain)


def shutdown_domain(uuid: str) -> DomainSummary:
    """Request a graceful shutdown. Idempotent: already-off is not an error."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state == DomainState.SHUTOFF:
        return summary
    try:
        domain.shutdown()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to shut down domain {uuid}: {exc}") from exc
    return _summarize(domain)


def force_stop_domain(uuid: str) -> DomainSummary:
    """Forcefully power off a domain. Idempotent: already-off is not an error."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state == DomainState.SHUTOFF:
        return summary
    try:
        domain.destroy()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to force-stop domain {uuid}: {exc}") from exc
    return _summarize(domain)


def reboot_domain(uuid: str) -> DomainSummary:
    """Request a guest reboot. A shut-off domain has nothing to reboot, so its state is returned."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state == DomainState.SHUTOFF:
        return summary
    try:
        domain.reboot()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to reboot domain {uuid}: {exc}") from exc
    return _summarize(domain)


def pause_domain(uuid: str) -> DomainSummary:
    """Suspend a running domain's vCPUs. Idempotent: already-paused is not an error."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state == DomainState.PAUSED:
        return summary
    if summary.state not in _PAUSABLE_STATES:
        raise InvalidDomainStateError(uuid, summary.state, "pause")
    try:
        domain.suspend()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to pause domain {uuid}: {exc}") from exc
    return _summarize(domain)


def resume_domain(uuid: str) -> DomainSummary:
    """Resume a paused domain. Idempotent: already-running is not an error."""
    domain = _lookup(uuid)
    summary = _summarize(domain)
    if summary.state in _PAUSABLE_STATES:
        return summary
    if summary.state != DomainState.PAUSED:
        raise InvalidDomainStateError(uuid, summary.state, "resume")
    try:
        domain.resume()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to resume domain {uuid}: {exc}") from exc
    return _summarize(domain)


def delete_domain(uuid: str) -> None:
    """Undefine a domain. Idempotent: already-deleted is not an error."""
    conn = get_connection()
    try:
        domain = conn.lookupByUUIDString(uuid)
    except libvirt.libvirtError:
        return
    try:
        if domain.isActive():
            domain.destroy()
        domain.undefine()
    except libvirt.libvirtError as exc:
        raise LibvirtLayerError(f"failed to delete domain {uuid}: {exc}") from exc
