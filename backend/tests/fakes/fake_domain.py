"""In-memory stand-ins for `libvirt.virDomain` and `libvirt.virConnect`.

Used to unit-test `app.libvirt.domains` without a hypervisor: tests patch
`app.libvirt.domains.get_connection` to return a `FakeConnection`. Only the
methods that module calls are implemented, and state transitions follow
libvirt's behavior closely enough to exercise the idempotency checks.
"""

import libvirt


class FakeDomain:
    def __init__(
        self,
        uuid: str = "11111111-1111-1111-1111-111111111111",
        name: str = "fake-vm",
        state: int = libvirt.VIR_DOMAIN_SHUTOFF,
    ) -> None:
        self._uuid = uuid
        self._name = name
        self.raw_state = state
        self.calls: list[str] = []

    def UUIDString(self) -> str:  # noqa: N802 - matches libvirt's API name
        return self._uuid

    def name(self) -> str:
        return self._name

    def isPersistent(self) -> int:  # noqa: N802 - matches libvirt's API name
        return 1

    def state(self) -> tuple[int, int]:
        return self.raw_state, 0

    def info(self) -> list[int]:
        return [self.raw_state, 1048576, 1048576, 2, 0]

    def _record(self, call: str) -> None:
        self.calls.append(call)

    def reboot(self) -> int:
        self._record("reboot")
        if self.raw_state == libvirt.VIR_DOMAIN_SHUTOFF:
            raise libvirt.libvirtError("Requested operation is not valid: domain is not running")
        return 0

    def suspend(self) -> int:
        self._record("suspend")
        self.raw_state = libvirt.VIR_DOMAIN_PAUSED
        return 0

    def resume(self) -> int:
        self._record("resume")
        self.raw_state = libvirt.VIR_DOMAIN_RUNNING
        return 0


class FakeConnection:
    def __init__(self, *domains: FakeDomain) -> None:
        self._domains = {d.UUIDString(): d for d in domains}

    def lookupByUUIDString(self, uuid: str) -> FakeDomain:  # noqa: N802 - libvirt's API name
        try:
            return self._domains[uuid]
        except KeyError as exc:
            message = f"Domain not found: no domain with matching uuid '{uuid}'"
            raise libvirt.libvirtError(message) from exc
