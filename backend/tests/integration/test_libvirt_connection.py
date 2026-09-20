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
