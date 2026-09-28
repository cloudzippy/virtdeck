import libvirt
import pytest

from app.libvirt import domains
from app.libvirt.domains import DomainState
from app.libvirt.exceptions import DomainNotFoundError, InvalidDomainStateError
from tests.fakes.fake_domain import FakeConnection, FakeDomain


def _use(monkeypatch: pytest.MonkeyPatch, domain: FakeDomain) -> None:
    monkeypatch.setattr(domains, "get_connection", lambda: FakeConnection(domain))


def test_reboot_shutoff_domain_returns_state_without_calling_libvirt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: rebooting a shut-off VM used to surface libvirt's error as a 502."""
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_SHUTOFF)
    _use(monkeypatch, domain)

    summary = domains.reboot_domain(domain.UUIDString())

    assert summary.state == DomainState.SHUTOFF
    assert domain.calls == []


def test_reboot_running_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_RUNNING)
    _use(monkeypatch, domain)

    summary = domains.reboot_domain(domain.UUIDString())

    assert summary.state == DomainState.RUNNING
    assert domain.calls == ["reboot"]


@pytest.mark.parametrize("state", [libvirt.VIR_DOMAIN_RUNNING, libvirt.VIR_DOMAIN_BLOCKED])
def test_pause_active_domain(monkeypatch: pytest.MonkeyPatch, state: int) -> None:
    domain = FakeDomain(state=state)
    _use(monkeypatch, domain)

    summary = domains.pause_domain(domain.UUIDString())

    assert summary.state == DomainState.PAUSED
    assert domain.calls == ["suspend"]


def test_pause_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_PAUSED)
    _use(monkeypatch, domain)

    summary = domains.pause_domain(domain.UUIDString())

    assert summary.state == DomainState.PAUSED
    assert domain.calls == []


def test_pause_shutoff_domain_is_a_state_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_SHUTOFF)
    _use(monkeypatch, domain)

    with pytest.raises(InvalidDomainStateError) as exc_info:
        domains.pause_domain(domain.UUIDString())

    assert exc_info.value.state == DomainState.SHUTOFF
    assert domain.calls == []


def test_resume_paused_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_PAUSED)
    _use(monkeypatch, domain)

    summary = domains.resume_domain(domain.UUIDString())

    assert summary.state == DomainState.RUNNING
    assert domain.calls == ["resume"]


def test_resume_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_RUNNING)
    _use(monkeypatch, domain)

    summary = domains.resume_domain(domain.UUIDString())

    assert summary.state == DomainState.RUNNING
    assert domain.calls == []


def test_resume_shutoff_domain_is_a_state_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = FakeDomain(state=libvirt.VIR_DOMAIN_SHUTOFF)
    _use(monkeypatch, domain)

    with pytest.raises(InvalidDomainStateError):
        domains.resume_domain(domain.UUIDString())

    assert domain.calls == []


def test_pause_unknown_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, FakeDomain())

    with pytest.raises(DomainNotFoundError):
        domains.pause_domain("22222222-2222-2222-2222-222222222222")
