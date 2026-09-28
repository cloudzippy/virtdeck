import pytest

from tests.conftest import LIBVIRT_IS_STUBBED

pytestmark = pytest.mark.integration


@pytest.mark.skipif(LIBVIRT_IS_STUBBED, reason="libvirt-python is not installed on this machine")
def test_list_domains_against_test_driver() -> None:
    """Sanity check against libvirt's built-in test driver (no real hypervisor needed)."""
    from app.libvirt import connection, domains

    connection.close_connection()
    try:
        summaries = domains.list_domains()
        assert len(summaries) >= 1
    finally:
        connection.close_connection()


@pytest.mark.skipif(LIBVIRT_IS_STUBBED, reason="libvirt-python is not installed on this machine")
def test_pause_resume_reboot_against_test_driver() -> None:
    """The test driver's state is in-memory per connection, so nothing persists past close."""
    from app.libvirt import connection, domains
    from app.libvirt.domains import DomainState

    connection.close_connection()
    try:
        running = next(d for d in domains.list_domains() if d.state == DomainState.RUNNING)

        assert domains.pause_domain(running.uuid).state == DomainState.PAUSED
        assert domains.pause_domain(running.uuid).state == DomainState.PAUSED
        assert domains.resume_domain(running.uuid).state == DomainState.RUNNING
        assert domains.resume_domain(running.uuid).state == DomainState.RUNNING

        domains.force_stop_domain(running.uuid)
        assert domains.reboot_domain(running.uuid).state == DomainState.SHUTOFF
    finally:
        connection.close_connection()
